import { test, expect } from "@playwright/test";

function silentWav() {
  const data = Buffer.alloc(364);
  data.write("RIFF", 0);
  data.writeUInt32LE(356, 4);
  data.write("WAVEfmt ", 8);
  data.writeUInt32LE(16, 16);
  data.writeUInt16LE(1, 20);
  data.writeUInt16LE(1, 22);
  data.writeUInt32LE(16000, 24);
  data.writeUInt32LE(32000, 28);
  data.writeUInt16LE(2, 32);
  data.writeUInt16LE(16, 34);
  data.write("data", 36);
  data.writeUInt32LE(320, 40);
  return data;
}

test("a voice answer preserves its original without creating a dream", async ({
  page,
  request,
}) => {
  const before = await (await request.get("/api/dreams")).json();
  await page.goto("/");
  await page.getByRole("button", { name: "Your World", exact: true }).click();
  await page
    .getByRole("button", { name: "What is asking for your attention?" })
    .click();
  await page
    .getByRole("button", { name: "Answer with a voice note", exact: true })
    .click();
  await page
    .getByLabel("Import answer recording", { exact: true })
    .setInputFiles({
      name: "answer.wav",
      mimeType: "audio/wav",
      buffer: silentWav(),
    });
  await page
    .getByRole("button", { name: "Save answer recording", exact: true })
    .click();
  await expect(
    page.getByText("Original recording saved.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Saved answer recording", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", {
      name: "Transcribe answer locally",
      exact: true,
    }),
  ).toBeEnabled();
  const after = await (await request.get("/api/dreams")).json();
  expect(after.length).toBe(before.length);
  await page.reload();
  await page.getByRole("button", { name: "Your World", exact: true }).click();
  await page
    .getByRole("button", { name: "What is asking for your attention?" })
    .click();
  await page
    .getByRole("button", { name: "Answer with a voice note", exact: true })
    .click();
  await expect(
    page.getByLabel("Saved recordings", { exact: true }),
  ).toBeVisible();
});

test("local voice transcript is reviewed before saving personal context", async ({
  page,
  request,
}) => {
  test.setTimeout(60000);
  const setup = await (await request.get("/api/transcription")).json();
  test.skip(!setup.ready, "Optional local voice tools are not installed");
  await page.goto("/");
  await page.getByRole("button", { name: "Your World", exact: true }).click();
  await page
    .getByRole("button", { name: "What is asking for your attention?" })
    .click();
  await page
    .getByRole("button", { name: "Answer with a voice note", exact: true })
    .click();
  await page
    .getByLabel("Import answer recording", { exact: true })
    .setInputFiles("../.dreamlit/voice/whisper.cpp-1.8.3/samples/jfk.wav");
  await page
    .getByRole("button", { name: "Save answer recording", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Transcribe answer locally", exact: true })
    .click();
  const transcript = page.getByRole("textbox", {
    name: "Review answer transcript",
    exact: true,
  });
  await expect(transcript).toContainText(/country/i, { timeout: 30000 });
  await transcript.fill("Learning to draw has been a welcome change.");
  await page
    .getByRole("button", { name: "Use reviewed answer", exact: true })
    .click();
  await expect(
    page.getByRole("textbox", { name: "Your answer", exact: true }),
  ).toHaveValue("Learning to draw has been a welcome change.");
  await page.getByRole("button", { name: "Save answer", exact: true }).click();
  await expect(
    page.getByText("Learning to draw has been a welcome change.", {
      exact: true,
    }),
  ).toBeVisible();
});
