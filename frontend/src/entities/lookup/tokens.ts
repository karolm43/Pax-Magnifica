import { tokens } from "@/entities/data/tokens";
import { indexBy } from "@/entities/lookup/indexBy";

const tokensMap = indexBy(tokens, (token) => token.id);

export const getTokenData = (tokenId: string) => tokensMap.get(tokenId);

/**
 * Lokalne korekty rozmiaru żetonów na mapie (dane AsyncTI4 nie mają dla nich `scale`).
 * Frontier stoi na KAŻDYM systemie bez planet i w skali 1 przytłaczał kafelek.
 */
const TOKEN_SCALE_OVERRIDES: Record<string, number> = {
  frontier: 0.6,
};

/** Skala żetonu na mapie — jedno źródło dla renderu i geometrii stosu. */
export const getTokenScale = (tokenId: string): number =>
  TOKEN_SCALE_OVERRIDES[tokenId] ?? getTokenData(tokenId)?.scale ?? 1;

export const getTokenImagePath = (tokenId: string): string | null => {
  const tokenData = getTokenData(tokenId);
  if (!tokenData) return null;
  return `/tokens/${tokenData.imagePath}`;
};
