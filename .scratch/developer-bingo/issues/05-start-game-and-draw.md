# 05: Start the game and draw

**What to build:** The host starts the game, which closes joining and locks the pool. The host draws one topic at a time. Every player sees the draw history and each drawn topic's explanation live.

**Blocked by:** 04 (Deal tickets on join)

**Status:** ready-for-agent

- [ ] Starting the game locks the pool and closes joining
- [ ] A draw picks uniformly at random from topics not yet drawn
- [ ] A topic is never drawn twice in a game
- [ ] Draws cannot happen before the game starts or after it ends
- [ ] Draws are final, with no undo
- [ ] Every player sees the draw history in order, live
- [ ] Every player sees each drawn topic's explanation
