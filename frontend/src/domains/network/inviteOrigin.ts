/**
 * Adres w linkach zaproszeń (RULES.md 44.6). Host gra na ``localhost`` — taki link nie działa
 * u znajomych, więc podmieniamy go na adresy tego komputera z lobby (LAN, ZeroTier…), z tym samym
 * protokołem i portem co strona (dev :5173, paczka .exe :8000). Gdy strona już działa pod adresem
 * sieciowym, zostaje on sam.
 */

const LOOPBACK = /^(localhost|127\.\d+\.\d+\.\d+|\[::1\])$/;

type PageLocation = Pick<Location, "protocol" | "hostname" | "port" | "origin">;

export function inviteOrigins(addresses: string[], location: PageLocation): string[] {
  if (!LOOPBACK.test(location.hostname) || addresses.length === 0) return [location.origin];
  const port = location.port ? `:${location.port}` : "";
  return addresses.map((ip) => `${location.protocol}//${ip}${port}`);
}
