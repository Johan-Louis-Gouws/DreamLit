import { expect, test, type Page } from "@playwright/test";

// This server owns a disposable journal; isolate each feature scenario.
test.beforeEach(async ({ request }) => {
  for (const record of await (
    await request.get("/api/insights/records")
  ).json()) {
    await request.delete(`/api/insights/records/${record.id}`);
  }
  for (const dream of await (await request.get("/api/dreams")).json()) {
    await request.delete(`/api/dreams/${dream.id}`);
  }
});

async function waitForInsight(page: Page, title: string) {
  await expect(
    page.getByRole("heading", { name: title, exact: true }),
  ).toBeVisible({
    timeout: 12_000,
  });
}

async function seedDreams(page: Page) {
  await page.request.post("/api/dreams", {
    data: {
      dreamed_on: "2026-09-08",
      text: "Maya asked for help at the garden gate and I walked away.",
      context: "I was tired after a long week.",
    },
  });
  await page.request.post("/api/dreams", {
    data: {
      dreamed_on: "2026-09-10",
      text: "Maya waited at the garden gate and I stayed to listen.",
      context: "We had spoken honestly that afternoon.",
    },
  });
}

test("answers retain revisions and people receive source-backed portraits", async ({
  page,
}) => {
  await seedDreams(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Your World", exact: true }).click();

  await page
    .getByRole("button", { name: "What is asking for your attention?" })
    .click();
  await page
    .getByRole("textbox", { name: "Your answer" })
    .fill("A difficult conversation with Maya.");
  await page.getByRole("button", { name: "Save answer", exact: true }).click();
  const answer = page.getByRole("article", {
    name: "Answer: What is asking for your attention?",
  });
  await expect(answer).toContainText("A difficult conversation with Maya.");
  await answer.getByRole("button", { name: "Edit answer" }).click();
  await page
    .getByRole("textbox", { name: "Your answer" })
    .fill("The conversation with Maya has changed.");
  await page.getByLabel("Answer status").selectOption("changed");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(answer).toContainText("Changed");
  await answer.getByRole("button", { name: "View history" }).click();
  await expect(
    page.getByRole("region", { name: "Record history" }),
  ).toContainText("A difficult conversation with Maya.");
  await page.getByRole("button", { name: "Close history" }).click();

  await page.getByRole("tab", { name: "People" }).click();
  await page.getByRole("button", { name: "Add a person" }).click();
  await page.getByLabel("Name").fill("Maya");
  await page.getByLabel("Aliases").fill("May");
  await page.getByLabel("Relationship").fill("A close friend");
  await page.getByLabel("Personal notes").fill("We met at school.");
  await page.getByRole("button", { name: "Save person" }).click();
  const person = page.getByRole("article", { name: "Person: Maya" });
  await person.getByRole("button", { name: "Generate portrait" }).click();
  await waitForInsight(page, "A relationship in your words");
  await page
    .getByRole("button", { name: /Open dream source/ })
    .first()
    .click();
  await expect(page.getByRole("dialog", { name: "Dream entry" })).toContainText(
    "Maya asked for help at the garden gate",
  );
});

test("turning points and investigations remain revisable through resolution", async ({
  page,
}) => {
  await seedDreams(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Explore", exact: true }).click();
  await page.getByRole("button", { name: "Compare turning points" }).click();
  await waitForInsight(page, "A different response");
  await expect(page.getByText(/\d+ of \d+ dreams included/)).toBeVisible();

  await page
    .getByRole("button", { name: "Investigate this turning point" })
    .click();
  await expect(page.getByLabel("Investigation question")).toHaveValue(
    "What feels different for you now?",
  );
  await page
    .getByLabel("Investigation question")
    .fill("When do I stay and listen?");
  await page
    .getByLabel("Investigation notes")
    .fill("Look for both distance and care.");
  await page.getByRole("button", { name: "Save investigation" }).click();
  const inquiry = page.getByRole("article", {
    name: "Investigation: When do I stay and listen?",
  });
  await inquiry.getByRole("button", { name: "Investigate this" }).click();
  await waitForInsight(page, "Examples and possibilities");
  await inquiry.getByRole("button", { name: "Edit investigation" }).click();
  await page
    .getByLabel("Conclusion")
    .fill("I stay when I name what I need first.");
  await page.getByLabel("Investigation status").selectOption("resolved");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(inquiry).toContainText("Resolved");
  await inquiry.getByRole("button", { name: "Reopen investigation" }).click();
  await expect(inquiry).toContainText("Open");
});

test("experiments record outcomes and weekly letters keep dated citations", async ({
  page,
}) => {
  await seedDreams(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Review", exact: true }).click();
  await page.getByRole("button", { name: "Plan an experiment" }).click();
  await page
    .getByLabel("Action")
    .fill("Pause before answering one difficult question.");
  await page.getByLabel("Intention").fill("Make room for an honest response.");
  await page.getByLabel("Check-in date").fill("2026-09-18");
  await page.getByRole("button", { name: "Save experiment" }).click();
  const experiment = page.getByRole("article", {
    name: "Experiment: Pause before answering one difficult question.",
  });
  await experiment.getByRole("button", { name: "Complete experiment" }).click();
  await page
    .getByLabel("Outcome")
    .fill("I listened before deciding what to say.");
  await page.getByRole("button", { name: "Save outcome" }).click();
  await expect(experiment).toContainText("Completed");
  await expect(experiment).toContainText(
    "I listened before deciding what to say.",
  );

  await page.getByRole("tab", { name: "Weekly Letter" }).click();
  await page.getByLabel("Week ending").fill("2026-09-11");
  await page.getByRole("button", { name: "Write weekly letter" }).click();
  await waitForInsight(page, "A letter from your week");
  await expect(page.getByText("Sep 5 – Sep 11, 2026").first()).toBeVisible();
  await page
    .getByRole("button", { name: /Open dream source/ })
    .first()
    .click();
  await expect(page.getByRole("dialog", { name: "Dream entry" })).toBeVisible();
});

test("reflection replies are saved as context only by deliberate action", async ({
  page,
}) => {
  await page.goto("/");
  for (const text of [
    "Nobody heard me at dinner.",
    "The phone would not dial.",
  ]) {
    await page
      .getByRole("textbox", { name: "What do you remember?" })
      .fill(text);
    await page.getByRole("button", { name: "Save dream", exact: true }).click();
    await expect(
      page.getByRole("textbox", { name: "What do you remember?" }),
    ).toHaveValue("");
  }
  await page.getByRole("button", { name: "Open entry" }).first().click();
  await page.getByRole("button", { name: "Analyse dream" }).click();
  await page.getByRole("button", { name: "Trying to communicate" }).click();
  const reflection = page.getByRole("dialog", { name: "Pattern reflection" });
  await reflection
    .getByLabel("Continue the reflection")
    .fill("I tend to wait until I feel certain.");
  await reflection.getByRole("button", { name: "Send reflection" }).click();
  await expect(
    reflection.getByText("Where does this situation show up while awake?"),
  ).toBeVisible({ timeout: 10_000 });
  await reflection
    .getByRole("button", { name: "Save reply as context" })
    .click();
  await expect(
    reflection.getByText("Saved to Your World", { exact: true }),
  ).toBeVisible();
  await reflection.getByRole("button", { name: "Close reflection" }).click();
  await page.getByRole("button", { name: "Your World", exact: true }).click();
  await expect(
    page.getByText("I tend to wait until I feel certain.", { exact: true }),
  ).toBeVisible();
});

test("insight navigation stays usable without horizontal phone overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  for (const button of await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("button")
    .all()) {
    const box = await button.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(390);
  }
  for (const name of ["Your World", "Explore", "Review"]) {
    await page.getByRole("button", { name, exact: true }).click();
    await expect(page.getByRole("heading").first()).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  }
});
