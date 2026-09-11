import { test, expect } from "@playwright/test";

async function capture(page, text: string) {
  await page.getByRole("button", { name: "Capture", exact: true }).click();
  await page.getByRole("textbox", { name: "What do you remember?" }).fill(text);
  await page.getByRole("button", { name: "Save dream", exact: true }).click();
  await expect(page.getByText("Dream saved", { exact: true })).toBeVisible();
}

test("save, reload, edit, and retain the original", async ({ page }) => {
  await page.goto("/");
  const original = "A copper boat waited for me. Journal persistence check.";
  await capture(page, original);
  await page.reload();
  await page.getByRole("button", { name: "Diary", exact: true }).click();
  await page.getByText(original, { exact: true }).first().click();
  const entry = page.getByRole("dialog", { name: "Dream entry" });
  await entry.getByRole("button", { name: "Edit entry", exact: true }).click();
  await entry
    .getByRole("textbox", { name: "Edit dream", exact: true })
    .fill("I remembered a silver boat instead.");
  await entry
    .getByRole("button", { name: "Save changes", exact: true })
    .click();
  await expect(
    entry.getByText("I remembered a silver boat instead.", { exact: true }),
  ).toBeVisible();
  await entry.getByRole("button", { name: "Original", exact: true }).click();
  await expect(entry.getByText(original, { exact: true })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(entry).not.toBeVisible();
});

test("open evidence, give feedback, and explicitly request the other provider", async ({
  page,
}) => {
  await page.goto("/");
  await capture(page, "Nobody heard me at dinner.");
  await capture(page, "The phone would not dial.");
  await page.getByRole("button", { name: "Open entry", exact: true }).click();
  await page
    .getByRole("button", { name: "Analyse dream", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Trying to communicate", exact: true })
    .click();
  const panel = page.getByRole("dialog", { name: "Pattern reflection" });
  await expect(
    panel.getByRole("region", { name: "Supporting dreams" }),
  ).toContainText("The phone would not dial.");
  await panel
    .getByRole("textbox", { name: "DOES THIS FIT YOUR EXPERIENCE?" })
    .fill("It was a practical communication issue.");
  await panel
    .getByRole("button", { name: "Does not fit", exact: true })
    .click();
  await expect(
    panel.getByText("Your perspective is saved for future reflections."),
  ).toBeVisible();
  await panel
    .getByRole("button", { name: "Ask Claude for a second opinion" })
    .click();
  await expect(
    panel.getByText("claude REFLECTION", { exact: true }),
  ).toBeVisible({ timeout: 10000 });
  await panel
    .getByRole("button", { name: "Close reflection", exact: true })
    .click();
  await page.getByRole("button", { name: "Connections", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Scan history", exact: true }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Scan history", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Scan finished", {
    timeout: 10000,
  });
  await page.getByRole("button", { name: "Timeline", exact: true }).click();
  await expect(
    page.getByText("The phone would not dial.", { exact: true }),
  ).toBeVisible();
});

test("phone layout has no sideways scrolling and keeps navigation usable", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Connections", exact: true }).click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Choose your guide" }),
  ).toBeVisible();
});

test("import audio and review local transcription before analysis", async ({
  page,
  request,
}) => {
  test.setTimeout(60000);
  const setup = await (await request.get("/api/transcription")).json();
  test.skip(!setup.ready, "Optional local transcription is not installed");
  await page.goto("/");
  await page.getByRole("button", { name: "Voice note", exact: true }).click();
  await page
    .locator("input[type=file]")
    .setInputFiles("../.dreamlit/voice/whisper.cpp-1.8.3/samples/jfk.wav");
  await page
    .getByRole("button", { name: "Save recording", exact: true })
    .click();
  await page.getByRole("button", { name: "Open entry", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Analyse dream", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Transcribe locally", exact: true })
    .click();
  const transcript = page.getByRole("textbox", { name: "Review transcript" });
  await expect(transcript).toContainText(/country/i, { timeout: 30000 });
  await transcript.fill("I remember the voice in the dream.");
  await page
    .getByRole("button", { name: "Use this transcript", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Analyse dream", exact: true }),
  ).toBeEnabled();
  await expect(
    page.getByText("I remember the voice in the dream.", { exact: true }),
  ).toBeVisible();
});
