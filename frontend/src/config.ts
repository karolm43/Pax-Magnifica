const devConfig = {
  api: {
    mapsUrl: "https://asyncti4.com/maps.json",
    proxyMapsUrl: "/proxy/maps.json",
    frogMapUrl:
      "https://qw2j1lld43.execute-api.us-east-1.amazonaws.com/Production/frog",
    discordLoginUrl: "http://localhost:8000/login",
    discordRedirectUri: "http://localhost:5173/login",
    gameDataUrl: "/bot/api/public/game",
    botApiUrl: "/bot/api",
    // Custodian Engine nie wystawia (na razie) STOMP; viewer działa przez refetch.
    // Wskazujemy lokalny adres, by nie łączyć się z produkcyjnym serwerem AsyncTI4.
    websocketUrl: "ws://127.0.0.1:8000/ws-stomp",
  },
};

const prodConfig = {
  api: {
    mapsUrl: "https://asyncti4.com/maps.json",
    proxyMapsUrl: "/proxy/maps.json",
    frogMapUrl:
      "https://qw2j1lld43.execute-api.us-east-1.amazonaws.com/Production/frog",
    discordLoginUrl: "https://api.asyncti4.com/login",
    discordRedirectUri: "https://asyncti4.com/login",
    gameDataUrl: "https://bot.asyncti4.com/api/public/game",
    botApiUrl: "https://bot.asyncti4.com/api",
    websocketUrl: "wss://bot.asyncti4.com/ws",
  },
};

export const config = import.meta.env.DEV ? devConfig : prodConfig;
