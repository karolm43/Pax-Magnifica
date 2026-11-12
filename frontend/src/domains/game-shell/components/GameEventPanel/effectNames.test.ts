import { describeEffectScope, resolveEffectName } from "./eventFormatting";

describe("nazwy efektów trwałych w historii", () => {
  it("klucz efektu zamienia na nazwę komponentu, nie surowe id", () => {
    expect(resolveEffectName("leaders:letnevhero")).toBe("Darktalon Treilla");
    expect(resolveEffectName("leaders:letnevagent:die")).toBe("Viscount Unlenn");
    expect(resolveEffectName("abilities:munitions")).toBe("Munitions Reserves");
  });

  it("zakres trwania po ludzku", () => {
    expect(describeEffectScope("round")).toBe("this game round");
    expect(describeEffectScope("combat_round")).toBe("this combat round");
  });
});
