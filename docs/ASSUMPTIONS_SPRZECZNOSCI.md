# Sprzeczności z `docs/rules_tirules/` (`CONTRADICTED` — 19 pozycji)

Poniżej lista miejsc, w których obecny wpis `ASSUMPTION` w `docs/rules/` stoi w sprzeczności z zasadami lub rulingami z `docs/rules_tirules/`. Część to świadome uproszczenia silnika, a część wymaga poprawy w kodzie/dokumentacji.

---

1. **[R01.md:L62](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules/R01.md#L62)** — **Ion Storm w entropic scar**
   - **Założenie**: żeton *Ion Storm* to frontier token z wormholem, więc zostaje w entropic scar.
   - **tirules** ([R_entropic_scars.md:L23](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/R_entropic_scars.md#L23)): *"If the Ion Storm exploration card would place its token in an entropic scar, the card is still placed in the common play area, and the token is discarded."*

2. **[R46.md:L34](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules/R46.md#L34)** — **Kolejność eksploracji wielu zdobytych planet**
   - **Założenie**: wszystkie zdobyte planety są już kontrolowane w momencie eksploracji.
   - **tirules** ([R_exploration.md:L33](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/R_exploration.md#L33)): *"If a player is to gain multiple planets in a system, they choose the order in which they gain them, and explore each planet as they gain it before gaining the next."*

3. **[R51.md:L85](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules/R51.md#L85)** — **Articles of War (agenda)**
   - **Założenie**: wyłącza tylko hooki zdolności mechów, a statystyki z danych (np. Bombardment L1Z1X, Space Cannon Xxcha, PRODUCTION Arborec) nadal działają.
   - **tirules** ([C_agendas.md:L29](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/C_agendas.md#L29)): *"Mechs lose all of their printed abilities other than Sustain Damage, including Bombardment, Space Cannon and Production. Their cost and combat values are unchanged, including any additional dice they roll..."*

4. **[R51.md:L91](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules/R51.md#L91)** — **Classified Document Leaks (agenda)**
   - **Założenie**: sekretny cel fazy akcji/agendy wybrany jako cel publiczny nie ma ścieżki punktowania.
   - **tirules** ([C_agendas.md:L52](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/C_agendas.md#L52)): *"A player can score a maximum of one objective of any type during or after each combat. A player cannot score the elected objective and one of their own secret objectives from the same combat."*

5. **[R53.md:L23](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules/R53.md#L23)** i **[R53.md:L75](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules/R53.md#L75)** — **Cechy planet (traits) z attachmentów**
   - **Założenie**: `exploration.planet_traits` i *Archaeological Expedition* ignorują traits nadane przez attachmenty (np. *Terraform*).
   - **tirules** ([R_attach.md](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/R_attach.md), [F_keleres.md](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/F_keleres.md), [F_ul.md](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/F_ul.md)): *"If Terraform is attached to Custodia Vigilia [or a planet in The Fracture], it may be explored."*

6. **[R53.md:L114](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules/R53.md#L114)** — **Sąsiedztwo bez hyperlanes** *(świadomie odłożone przez użytkownika 2026-11-27)*
   - **Założenie**: sąsiedztwo nie uwzględnia hyperlanes.
   - **tirules** ([R_hyperlanes.md](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/R_hyperlanes.md)): *"Systems that are connected by lines drawn across one or more hyperlane tiles are adjacent for all purposes."*

7. **[R53.md:L125](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules/R53.md#L125)** — **Signal Jamming (karta akcji)**
   - **Założenie**: gracz, który ma już żeton w systemie, nie może być celem.
   - **tirules** ([R_command_tokens.md](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/R_command_tokens.md)): *"If a game effect would place a player’s command token in a system where they already have one, they place the token in their reinforcements instead. Any effects that resolve by placing that token are resolved as normal."*

8. **[R53.md:L127](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules/R53.md#L127)** — **Pirate Contract (karta akcji)**
   - **Założenie**: jednostki neutralne nie mają rezerw ani limitu sztuk.
   - **tirules** ([R_neutral_units.md](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/R_neutral_units.md)): *"If there are no neutral units of a given type left in the supply, and one would be placed, it is not placed."*

9. **[R53.md:L253](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules/R53.md#L253)** — **Skilled Retreat (karta akcji)** *(stary wpis; poprawione niżej w `R53.md:L368`)*
   - **Założenie**: żeton tylko z rezerw (brak żetonu = brak położenia).
   - **tirules** ([C_action_cards.md](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/C_action_cards.md)): *"If a player has no command tokens in their reinforcements, they must take one from any pool of their command sheet and place that instead."*

10. **[R53.md:L262](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules/R53.md#L262)** — **Reflective Shielding (karta akcji)**
    - **Założenie**: grywalna tylko, gdy przeciwnik jeszcze nie przypisał strat.
    - **tirules** ([C_action_cards.md](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/C_action_cards.md)): *"If Reflective Shielding is played after a ship uses its Sustain Damage ability at any other time during combat, the hits are assigned immediately."*

11. **[R53.md:L300](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules/R53.md#L300)** — **Crash Landing (karta akcji)**
    - **Założenie**: w kroku Invasion automatycznie wybucha walka naziemna nawet bez Commit.
    - **tirules** ([R_invasion.md](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/R_invasion.md), [R_coexistence.md](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/R_coexistence.md)): *"Coexisting units do not trigger a ground combat, but the active player may choose to engage them with ground forces committed to that planet."*

12. **[R54.md:L18](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules/R54.md#L18)** (pkt a) — **Kolejność w oknie `REACTION`** *(świadomie odłożone przez użytkownika 2026-11-27)*
    - **Założenie**: okno obsługuje oferty graczy po kolei bez przeplatania po jednej zdolności.
    - **tirules** ([R_abilities.md:L70–71](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/R_abilities.md#L70-L71)): *"If a player has multiple abilities they wish to resolve, they must be resolved one at a time. Between each ability being resolved, each other player will have the opportunity to resolve one ability."*

13. **[R56.md:L19](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules/R56.md#L19)** — **Assault Cannon (technologia)**
    - **Założenie**: całe okno startu walki przeciwników poprzedza Assault Cannon (można użyć >1 zdolności).
    - **tirules** ([C_technology.md:L151](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/C_technology.md#L151)): *"Each other player may use one ability after that player has gained ships, and before that player has the opportunity to use the Assault Cannon ability."*

14. **[R59.md:L12](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules/R59.md#L12)** — **Book of Latvinia (relikt)**
    - **Założenie**: pominięto wyjątek Nekro (6 żetonów zamiast technologii).
    - **tirules** ([C_relics.md:L11](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/C_relics.md#L11)): *"If the Nekro player draws the Book of Latvinia, they will gain six command tokens and zero technologies, even if they own all technologies without prerequisites."*

15. **[R59.md:L20](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules/R59.md#L20)** — **The Silver Flame (relikt)**
    - **Założenie**: „purge home system” usuwa jednostki i planety, ale kafelek zostaje na planszy.
    - **tirules** ([R_purge.md:L10](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/R_purge.md#L10), [C_relics.md:L117](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/C_relics.md#L117)): *"that component is removed from the game and returned to the box."*

16. **[R61.md:L27](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules/R61.md#L27)** — **Trade Agreement (notka)** *(uproszczenie okna reakcji)*
    - **Założenie**: okno otwarte aż do następnej akcji.
    - **tirules** ([R_abilities.md:L31, L62–63](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/R_abilities.md#L31)): *"If the timing of an ability uses the word 'when', the ability’s effect occurs at the moment of the described timing event."*

17. **[R62.md:L298](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules/R62.md#L298)** — **Conservator Procyon / Multiverse Shift (Empyrean)**
    - **Założenie**: kolejność eksploracji tokenów frontier jest ustalona po pozycjach na planszy.
    - **tirules** ([R_exploration.md:L15](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/R_exploration.md#L15)): *"If a player gains control of multiple planets or resolves multiple explore effects at the same time, they choose the order in which they resolve those explorations..."*

18. **[R62.md:L370](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules/R62.md#L370)** — **The Alastor (Nekro)** *(znany gap)*
    - **Założenie / gap**: nie można jeszcze wybrać ground forces z planet w systemie.
    - **tirules** ([F_nekro.md:L92–93](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/F_nekro.md#L92-L93)): *"Ground forces on planets remain there while participating in combat."*

19. **[R66.md:L20](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules/R66.md#L20)** — **Moment eliminacji gracza**
    - **Założenie**: eliminacja z efektu w fazie agendy/statusu jest wykrywana dopiero na końcu kolejnej tury fazy akcji.
    - **tirules** ([R_elimination.md:L10–13](file:///C:/Users/Karol/Desktop/Pax%20Magnifica/docs/rules_tirules/R_elimination.md#L10-L13)): *"A player is eliminated when they meet all of the following three conditions..."* (eliminacja następuje od razu w momencie spełnienia warunków).
