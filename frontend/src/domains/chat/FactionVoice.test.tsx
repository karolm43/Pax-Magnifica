import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import type { ChatMessage } from "@/api/useBoardEditor";
import { FactionVoice, FactionVoiceBubble } from "./FactionVoice";

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
vi.mock("@/entities/lore/factionVoiceLines", () => ({
  VOICE_CATEGORIES: [
    { id: "quote", label: "Quote" },
    { id: "taunt", label: "Taunt" },
  ],
  voiceLinesFor: (faction: string, category: string) =>
    faction === "sol" ? [category === "quote" ? "Sol quote" : "Hold the line."] : [],
  pickVoiceLine: (faction: string, category: string) =>
    faction === "sol" ? (category === "quote" ? "Sol quote" : "Hold the line.") : null,
}));

const voice = (seq: number, sender: string, text: string): ChatMessage => ({
  seq,
  sender,
  to: null,
  whisper: false,
  text,
  at: seq,
  voice: true,
});

describe("FactionVoice - komunikaty frakcji", () => {
  beforeEach(() => {
    sendChat.mockClear();
    messages = [];
  });

  it("własny gracz: przyciski kategorii, klik wysyła kwestię z kategorii jako voice", async () => {
    render(<FactionVoice playerId="p1" faction="sol" />);
    fireEvent.click(screen.getByRole("button", { name: "Faction voice lines" }));
    fireEvent.click(await screen.findByRole("button", { name: "Taunt" }));
    await waitFor(() => expect(sendChat).toHaveBeenCalledWith("p1", "Hold the line.", null, true));
  });

  it("kategoria bez kwestii jest wyszarzona", async () => {
    render(<FactionVoice playerId="p1" faction="hacan" />);
    fireEvent.click(screen.getByRole("button", { name: "Faction voice lines" }));
    const taunt = await screen.findByRole("button", { name: "Taunt" });
    expect((taunt as HTMLButtonElement).disabled).toBe(true);
  });

  it("cudzy gracz nie ma przycisku komunikatów", () => {
    const { container } = render(<FactionVoice playerId="p2" faction="hacan" />);
    expect(container.textContent).toBe("");
  });

  it("dymek nad polem gracza: tylko NOWA kwestia (nie stara), z podpisem frakcji", () => {
    messages = [voice(1, "p2", "old line")];
    const bubble = <FactionVoiceBubble playerId="p2" author="The Emirates of Hacan" />;
    const { rerender } = render(bubble);
    expect(screen.queryByRole("status")).toBeNull();
    messages = [...messages, voice(2, "p2", "Trade is war by other means.")];
    rerender(<FactionVoiceBubble playerId="p2" author="The Emirates of Hacan" />);
    const status = screen.getByRole("status");
    expect(status.textContent).toContain("Trade is war by other means.");
    expect(status.textContent).toContain("The Emirates of Hacan");
  });
});
