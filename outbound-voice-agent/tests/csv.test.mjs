import assert from "node:assert/strict";
import test from "node:test";

import { parseCsv, toCsvRow } from "../src/csv.mjs";

test("parseCsv reads simple records", () => {
  const records = parseCsv("id,name\n1,Avery\n2,Sofia\n");

  assert.deepEqual(records, [
    { id: "1", name: "Avery" },
    { id: "2", name: "Sofia" }
  ]);
});

test("toCsvRow escapes commas, quotes, and newlines", () => {
  assert.equal(
    toCsvRow(["assistant", "She said \"hello\", then paused.\nDone."]),
    "assistant,\"She said \"\"hello\"\", then paused.\nDone.\""
  );
});
