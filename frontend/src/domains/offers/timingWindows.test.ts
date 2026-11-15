import { describe, expect, it } from "vitest";
import { CLOSED_NOTICE_MS, goneSince, mergeGone, type Gone } from "./timingWindows";

const key = (s: string) => s;

describe("timing window lifecycle (RULES.md 54.9)", () => {
  it("finds windows that closed since the last refresh", () => {
    expect(goneSince(["won", "round"], ["round"], key)).toEqual(["won"]);
    expect(goneSince([], ["round"], key)).toEqual([]);
  });

  it("keeps a closed window for the notice time, then drops it", () => {
    const first = mergeGone<string>([], ["won"], [], key, 1000);
    expect(first).toEqual([{ item: "won", until: 1000 + CLOSED_NOTICE_MS }]);
    expect(mergeGone(first, [], [], key, 1000 + CLOSED_NOTICE_MS + 1)).toEqual([]);
  });

  it("drops a closed window that opened again and returns the same array when nothing changed", () => {
    const gone: Gone<string>[] = [{ item: "won", until: 9999 }];
    expect(mergeGone(gone, [], ["won"], key, 0)).toEqual([]);
    expect(mergeGone(gone, [], [], key, 0)).toBe(gone);
  });

  it("does not duplicate a window that closes twice", () => {
    const gone: Gone<string>[] = [{ item: "won", until: 9999 }];
    expect(mergeGone(gone, ["won"], [], key, 0)).toBe(gone);
  });
});
