import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { vi } from "vitest";
import type { ChatMessage } from "@/api/useBoardEditor";
import { ChatPanel } from "./ChatPanel";

const sendChat = vi.fn(() => Promise.resolve());
let messages: ChatMessage[] = [];

vi.mock("@/api/useBoardEditor", () => ({
  useBoardEditor: () => ({ sendChat }),
  useActivityFeed: () => ({ data: { players: {} } }),
  useChat: () => ({ data: messages }),
}));
vi.mock("@/domains/network/useNetworkMe", () => ({
  useNetworkMe: () => ({ data: { network: true, player_id: "p1" } }),
}));
vi.mock("@/state/useGameContext", () => ({
  useGameData: () => ({
    playerData: [
      { discordId: "p1", color: "red", faction: "sol", userName: "Ann" },
      { discordId: "p2", color: "blue", faction: "hacan", userName: "Bob" },
      { discordId: "p3", color: "green", faction: "xxcha", userName: "Cy" },
    ],
  }),
}));

describe("ChatPanel - czat i szepty (RULES.md 47.6)", () => {
  beforeEach(() => {
    localStorage.clear();
    sendChat.mockClear();
    messages = [
      { seq: 1, sender: "p2", to: null, whisper: false, text: "hello all", at: 0 },
      // Cudzy szept: backend nie wysyła treści - widać tylko, KTO do KOGO szepcze.
      { seq: 2, sender: "p2", to: "p3", whisper: true, text: null, at: 1 },
      { seq: 3, sender: "p3", to: "p1", whisper: true, text: "deal?", at: 2 },
    ];
  });

  it("zwinięty: mała ikonka z licznikiem nieprzeczytanych", () => {
    render(<ChatPanel />);
    expect(screen.getByRole("button", { name: "Open chat (3 unread)" })).toBeTruthy();
    expect(screen.queryByRole("region", { name: "Chat" })).toBeNull();
  });

  it("cudzy szept pokazuje tylko fakt szeptu, mój szept - treść", () => {
    render(<ChatPanel />);
    fireEvent.click(screen.getByRole("button", { name: /Open chat/ }));
    const panel = screen.getByRole("region", { name: "Chat" });
    const lines = within(panel).getAllByRole("listitem");
    expect(lines[0].textContent).toContain("hello all");
    expect(lines[1].textContent).toContain("whispers to");
    expect(lines[2].textContent).toContain("deal?");
    // Otwarcie = przeczytane; minimalizacja wraca do ikonki bez licznika.
    fireEvent.click(within(panel).getByRole("button", { name: "Minimize chat" }));
    expect(screen.getByRole("button", { name: "Open chat" })).toBeTruthy();
  });

  it("szept: wybór gracza chipem i wysłanie Enterem", async () => {
    render(<ChatPanel />);
    fireEvent.click(screen.getByRole("button", { name: /Open chat/ }));
    fireEvent.click(screen.getByRole("button", { name: "Whisper to Bob" }));
    const input = screen.getByRole("textbox", { name: "Message" });
    fireEvent.change(input, { target: { value: "  secret  " } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(sendChat).toHaveBeenCalledWith("p1", "secret", "p2");
    await waitFor(() => expect((input as HTMLInputElement).value).toBe(""));
    // „All” = do wszystkich.
    fireEvent.click(screen.getByRole("button", { name: "All" }));
    fireEvent.change(input, { target: { value: "hi" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(sendChat).toHaveBeenLastCalledWith("p1", "hi", null);
  });
});
