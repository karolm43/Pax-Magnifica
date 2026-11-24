# Space Combat

> Źródło: [https://www.tirules2.com/R_space_combat](https://www.tirules2.com/R_space_combat) — treść reguł © Fantasy Flight Games.
> Zrzut z repo tirules (GPL-3.0). Patrz `SOURCE.md`.

## Rules Reference

After resolving the **Space Cannon Offense** step of a tactical action, if two players have ships in the active system, those players must resolve a space combat.

- If the active player is the only player with ships in the system, they skip the **Space Combat** step of the tactical action and proceeds to the **Invasion** step.
- If an ability occurs “before combat”, it occurs immediately before the **Anti–Fighter Barrage** step.
    - During the first round of a combat, “start of combat” and “start of combat round” effects occur during the same timing window.
    - During the last round of a combat, “end of combat” and “end of combat round” effects occur during the same timing window.

To resolve a space combat, players perform the following steps:

- **Step 1 – Anti–Fighter Barrage**: If this is the first round of a space combat, the players may simultaneously use the `Anti–Fighter Barrage` ability of any of their units in the active system.
    - If one or both players no longer have ships in the active system after resolving this step, the space combat ends immediately.
    - Players cannot resolve `Anti–Fighter Barrage` abilities during any rounds of space combat other than the first round.
    - This step still occurs if no fighters are present.
- **Step 2 – Announce Retreats**: Each player may announce a retreat, beginning with the defender.
    - A retreat will not occur immediately; the units retreat during the **Retreat** step.
    - If the defender announces a retreat, the attacker cannot announce a retreat during that combat round.
    - A player cannot announce a retreat if there is not at least one eligible system to retreat to.
- **Step 3 – Roll Dice**: Each player rolls one die for each ship they have in the active system; this is called a combat roll. If a unit’s combat roll produces a result that is equal to or greater than that unit’s combat value, that result produces a hit.
    - If a unit’s combat value contains two or more burst icons, the player rolls one die for each burst icon instead.
    - If a player has ships that have different combat values in the active system, that player rolls these dice separately.
    - First, that player should roll all dice for units with a combat value of “1”. Then, that player should roll all dice for units with combat value of “2”, and then “3”, continuing in numerical order until that player has rolled dice for each of their ships.
    - The player counts each hit their combat rolls produce. The total number of hits produced will destroy units during the **Assign Hits** step.
    - If a player has an ability that rerolls a die or affects a die after it is rolled, that player must resolve such an ability immediately after rolling all of their dice.
    - The attacker makes all of their combat rolls during this step before the defender. This procedure is important for abilities that allow a player to reroll an opponent’s die.
- **Step 4 – Assign Hits**: Each player in the combat must choose and destroy one of their own ships in the active system for each hit their opponent produced.
    - Before assigning hits, players may use their units’ `Sustain Damage` abilities to cancel hits.
    - When a unit is destroyed, the player who controls that unit removes it from the board and places it in their reinforcements.
- **Step 5 – Retreat**: If a player announced a retreat during **step 2**, and there is still an eligible system for their units to retreat to, they must retreat.
    - If a player announced a retreat during the **Announce Retreats** step, but their opponent has no ships remaining in the system, the combat immediately ends and the retreat does not occur.
    - To retreat, a player takes all of their ships with a move value in the combat and moves them to a single system that is adjacent to the active system. That player’s fighters and ground forces in the space area of the active system that are unable to move or be transported are removed.
    - The system that a player’s units retreat to must contain one or more of that player’s units, a planet they control, or both. Additionally, the system cannot contain ships controlled by another player.
    - If any of a player’s units successfully retreat and are moved into an adjacent system, that player must place a command token from their reinforcements in the system to which their units retreated. If that system already contains one of their command tokens, that player does not place an additional token there. If the player has no command tokens in their reinforcements, that player must use one from their command sheet instead.
- After the **Retreat** step, if both players still have ships in the active system, those players resolve another round of space combat beginning with the **Announce Retreats** step.
- Space combat ends when only one player – or neither player – has a ship in the space area of the active system.
    - During the last round of a combat, “end of combat” and “end of combat round” effects occur during the same timing window.
- After a combat ends, the player with one or more ships remaining in the system is the winner of the combat; the other player is the loser of the combat. If neither player has a ship remaining, the combat ends in a draw and there is no winner.
    - If the winner of the combat has fighters or ground forces in the space area of the active system and those units exceed the capacity of that player’s ships in that system, that player must choose and remove any excess units.

## Notes

- Abilities that resolve at the start of a space combat, such as the *Assault Cannon* technology and the [Mentak](https://www.tirules2.com/F_mentak) player’s [`Ambush`](https://twilight-imperium.fandom.com/wiki/The_Mentak_Coalition#Faction_Abilities:~:text=Ambush) faction ability, are resolved before the **Anti–Fighter Barrage** step.
- Abilities that trigger “at the start of a combat”, other than those on agents, can only be resolved during a combat in which the player resolving them is participating.
- A player’s fighters and ground forces do not count against capacity during combat. At the end of combat, any excess units are removed and returned to that player’s reinforcements.
- Capacity is checked after the winner of a space combat is determined.
    - It is possible to win a space combat with only fighters remaining, before those fighters are removed due to lack of capacity.
- The following apply to retreats:
    - Ships that have announced a retreat still roll dice during the Roll Dice step of that combat round, then retreat during the Retreat step. Retreating this way avoids abilities that resolve after the combat round, such as the [N’orr](https://www.tirules2.com/F_norr) player’s [*Exotrireme II*](https://twilight-imperium.fandom.com/wiki/Sardakk_N'orr#:~:text=Exotrireme).
    - If a space combat reaches a state where neither player can win, the attacker must retreat. If the attacker cannot retreat, their units in that combat are destroyed.
    - Modifying the move value of a ship will have no effect when retreating. Retreats are limited to adjacent systems.
    - The *Dark Energy Tap* technology allows a player to retreat into a system that does not contain their ships or a planet they control.
    - Ships can retreat into a nebula, as a nebula is intended to no longer need to be the active system for units to move into it.
    - A player can retreat into an asteroid field or supernova only if an effect allows their ships to move into it, such as the *Antimass Deflectors* technology or the [Muaat](https://www.tirules2.com/F_muaat) player’s [*Magmus Reactor*](https://twilight-imperium.fandom.com/wiki/The_Embers_of_Muaat#Faction_Technologies:~:text=Magmus%20Reactor) technology.*
    - Ships retreating out of a gravity rift are affected by it; see [Gravity Rift](https://www.tirules2.com/R_gravity_rift).
    - The *Nav Suite* action card will not allow a player to ignore an anomaly while retreating, as a retreat does not happen during the **Movement** step.*
    - Ships can retreat out of the active system, and transport units out of it, even if it contains the retreating player’s command token.
    - While retreating, a player may transport zero or more ground forces from planets they control in the active system. The player need not decide which ground forces they transport until they execute the retreat.
    - While retreating, a player cannot transport more fighters and/or ground forces than they have capacity in the retreating ships.
    - When a player retreats, their fighters that remain in the space area of the active system are removed, even if that system contains one of their space docks.
    - Ground forces transported by retreating ships, or moved with the *Skilled Retreat* action card, cannot land on planets in the system they move to; they remain in the space area.
- A player only wins a combat if a space combat or ground combat occurred. Destroying all opposing ships with the Space Cannon ability, destroying all opposing ground forces with the Bombardment ability, landing ground forces on a planet without opposing ground forces, or the opposing player avoiding the combat with the [Naalu](https://www.tirules2.com/F_naalu) player’s Foresight faction ability does not count as winning a combat. A planet containing only another player’s structures does not cause a ground combat.
- The “0” side of the d10 represents a result of 10.

## Related Topics

- [Anti–Fighter Barrage](https://www.tirules2.com/R_anti_fighter_barrage)
- [Attacker](https://www.tirules2.com/R_attacker)
- [Capacity](https://www.tirules2.com/R_capacity)
- [Defender](https://www.tirules2.com/R_defender)
- [Destroyed](https://www.tirules2.com/R_destroyed)
- [Fleet Pool](https://www.tirules2.com/R_fleet_pool)
- [Opponent](https://www.tirules2.com/R_opponent)
- [Sustain Damage](https://www.tirules2.com/R_sustain_damage)
- [Tactical Action](https://www.tirules2.com/R_tactical_action)
- [Transport](https://www.tirules2.com/R_transport)
