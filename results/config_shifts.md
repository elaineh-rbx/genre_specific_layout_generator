# Config shift analysis

Diff between the upstream skill's first-pass config (prompt only)
and the answered config (prompt + author-answered clarifications).

## Summary
scenes compared: 614

agreement between upstream first-pass and answered config:
  genre     462/614  (75% agree, 152 shifted)
  shape     356/614  (57% agree, 258 shifted)
  preset    254/614  (41% agree, 360 shifted)
  route     329/614  (53% agree, 285 shifted)
  options   124/614  (20% identical set, 490 changed the picked set)

scenes by number of axes shifted (out of 5):
  0 axis unchanged: 97
  1 axis shifted: 100
  2 axis shifted: 110
  3 axis shifted: 90
  4 axis shifted: 130
  5 axis shifted: 87

## Genre shifts
top genre shifts (of 152 shifted scenes):
    27                              (none)  ->  Entertainment (Showcase & Hub)
     7                              (none)  ->  Simulation
     6               Roleplay & Avatar Sim  ->  Entertainment (Showcase & Hub)
     6                           Adventure  ->  Survival
     6               Roleplay & Avatar Sim  ->  Party & Casual
     5                              Action  ->  RPG
     5                             Shooter  ->  Survival
     4                              Racing  ->  Simulation
     3               Roleplay & Avatar Sim  ->  Survival
     3               Roleplay & Avatar Sim  ->  Simulation

examples of top genre shifts (up to 3 per transition):

  (none) -> Entertainment (Showcase & Hub)  (27 scenes)
    P0225  a forest with birds flying around and people are their own avatars just a chill game
    P0240  Let's make a party scene! In 3d
    P0250  I want to build a 3D game for multi player painting in a playground. The players should have a brush tool. When they paint on surfaces, the strokes are made of 

  (none) -> Simulation  (7 scenes)
    P0208  make a game called do nothing point idle where its just a black box with lights in the top corners of the room and all they can do is flick the lights on and of
    P0334  Lets start with a simple baseplate where the player is a physics based vehicle, for now no model but I want to have the player to be spawned into a floating par
    P0335  I want to build a realistic skateboard game that has flick it controls on screen, I should be able to pull down to prep a trick, then flick up to Ollie, to the 

  Roleplay & Avatar Sim -> Entertainment (Showcase & Hub)  (6 scenes)
    P0033  Create a game where you walk in forests and trails with your customizable dog
    P0042  an avatar buying game with a cute pink map and avatar decals to buy off of
    P0131  hi I wana make a game wear u can dress up and go on a run way or u can go make an outfit and post it on a fake like thing

  Adventure -> Survival  (6 scenes)
    P0040  I want a duck game where you have to migrate from New Zealand to Canada by fly across storms and rough seas
    P0150  hi I would like to make a game called Elements Monsters\nso players go in a area saying Come in the circle for chapter 1.\nFirst there's a cut seen, players fol
    P0193  Game Name (working title)\nLAST ROUTE\n"No one knows why the road is still open."\nCore Idea\nYou and up to 5 friends are driving one truck across a frozen moun

  Roleplay & Avatar Sim -> Party & Casual  (6 scenes)
    P0128  classic lobby game but you have to design your avatar by going through doors every now and then
    P0132  hi can U make a dress up game where there is a VIP area and U must use robux to go in and it cost 221 robux and a free area for all players and can U make ranki
    P0136  a 3d dti but it's called fashion week and you wake up on a bed walk into your closet and pick an outfit a y2k, cute core, or emo or big puffy dresses and you ha

  Action -> RPG  (5 scenes)
    P0061  ⚔️ ROBLOX FIGHTING SIMULATOR - FULL GAME PLAN\n\n🎮 GAME IDEA\n\nA fast-paced fighting simulator where players train stats, unlock abilities, and battle other pl
    P0066  Make a 3D game where you have to kill slime monsters. They have cool animations, jump, and textures. A large map with such a terrain. You have to kill them in y
    P0067  Crie um jogo de batalhas de Beyblade inspirado no estilo de Tops Totalmente Preciso, mas com mapa, modelos, interface e código totalmente originais.\n\nO jogo d

## Shape shifts
top shape shifts (of 258 shifted scenes):
    22                              (none)  ->  showcase-freeroam
    10                   showcase-freeroam  ->  venue-stage
     8                   world-open-biomes  ->  world-single
     8                    space-continuous  ->  space-staged
     7                              (none)  ->  world-shared
     5                      warren-looping  ->  arena-contained
     5                        world-biomes  ->  arena-contained
     5                settlement-buildable  ->  settlement-claimable
     5                         plot-shared  ->  plot-isolated
     4                   world-open-biomes  ->  world-hub-dungeon

examples of top shape shifts (up to 3 per transition):

  (none) -> showcase-freeroam  (22 scenes)
    P0225  a forest with birds flying around and people are their own avatars just a chill game
    P0240  Let's make a party scene! In 3d
    P0250  I want to build a 3D game for multi player painting in a playground. The players should have a brush tool. When they paint on surfaces, the strokes are made of 

  showcase-freeroam -> venue-stage  (10 scenes)
    P0258  create a music performance where there is a 3d rendered punk rock star on stage with a screen in the back ground. The rockstar is generating music energy render
    P0259  let's create a 3D game that lets you create 1-song "concerts" by choosing: an avatar, a song, a stage, and environment and then allows you to capture it with mo
    P0260  Make a Constert Stage game with Bulit in music to use and house lights

  world-open-biomes -> world-single  (8 scenes)
    P0016  create an open world 3d game about killing enemies, leveling up, increasing statsamd unlock areas. add a menu where theres a shop system, settings. add a advanc
    P0017  low graphics long storyline mobile-related Mech game at the start you are ejected from a warship down onto a planet landing in a forest the forest is named ayus
    P0021  recreate blox fruits but the powers are based off jujutsu kaisen cursed techniques the islands are based off area in Japan the quests are based off the storylin

  space-continuous -> space-staged  (8 scenes)
    P0076  I would like a game when you can play tag and 1v1 want a maps as forest desert snow
    P0077  cheat the game cheat you run around a park and if you get caught buy the taga when you are on the ground you in when the timer runs out the player that is in ge
    P0080  I want to create a game were there's goose that chace u and ur a duck and when u get tagged u become a goose and u can win so much cool avatar stuff and there's

  (none) -> world-shared  (7 scenes)
    P0208  make a game called do nothing point idle where its just a black box with lights in the top corners of the room and all they can do is flick the lights on and of
    P0334  Lets start with a simple baseplate where the player is a physics based vehicle, for now no model but I want to have the player to be spawned into a floating par
    P0335  I want to build a realistic skateboard game that has flick it controls on screen, I should be able to pull down to prep a trick, then flick up to Ollie, to the 

  warren-looping -> arena-contained  (5 scenes)
    P0151  make a 3D horror game called survive the rake and make the map a giant forest and it's super dark your stuck in first person and all you have is a flash light m
    P0158  Roblox Horror Game Prompt - Yourself\n\nGame Title: Yourself\n\nCreate a polished multiplayer Roblox horror game called "Yourself." The main enemy is a dark, co
    P0267  make a game that is scary and there are monsters in the forest 3D. And its like a hide an seek game but when they find you there are items all across the map to

## Preset shifts
top preset shifts (of 360 shifted scenes):
    19                         Vehicle Sim  ->  none
    17                      Morph Roleplay  ->  none
    10                  Free-Roam Showcase  ->  Performance Venue
     9                         PvE Shooter  ->  none
     9                    Explorable Place  ->  none
     8           Open World & Survival RPG  ->  none
     8                          Animal Sim  ->  none
     8                         Exploration  ->  none
     8               Incremental Simulator  ->  none
     8                      Childhood Game  ->  Minigame

examples of top preset shifts (up to 3 per transition):

  Vehicle Sim -> none  (19 scenes)
    P0284  build a 3D game where I fly my UFO over a landscape, beaming up cows and avoiding airplanes
    P0404  Creant an experience based on aqualife. Players can enjoy the pedal boat riding in the pond. If any of duclings or fish came in front of their boat then they ha
    P0408  American plains mudding game

  Morph Roleplay -> none  (17 scenes)
    P0042  an avatar buying game with a cute pink map and avatar decals to buy off of
    P0126  i want to build a avatar catalog editor like game where users can choose a avatar outfit from the avatar shops in the experience.
    P0127  can you please make a game where u dress up and you have a opportunity for skinny, muscle and fat body tips with opportunity of clothes and you can walk around 

  Free-Roam Showcase -> Performance Venue  (10 scenes)
    P0258  create a music performance where there is a 3d rendered punk rock star on stage with a screen in the back ground. The rockstar is generating music energy render
    P0259  let's create a 3D game that lets you create 1-song "concerts" by choosing: an avatar, a song, a stage, and environment and then allows you to capture it with mo
    P0260  Make a Constert Stage game with Bulit in music to use and house lights

  PvE Shooter -> none  (9 scenes)
    P0109  Make a shooting game set in a Walmart, but call it Tops Supermarket, and you shoot cornflakes at the other shoppers. When a shopper is hit they fall down and st
    P0298  OUTBREAK GENESIS - PROMPT 1: FOUNDATION BUILD\n\nCreate the foundation for a polished Roblox third-person co-op roguelite shooter called Outbreak Genesis.\n\nDo
    P0341  a 3D neon-wireframe tank arena shooter (Tron style) where you drive a tank around an open arena, aim a crosshair and fire at enemy tanks, and survive waves of i

  Explorable Place -> none  (9 scenes)
    P0302  Haz un juego 3d de una ciudad enorme y tu apretás un botón y con ese botón te puedes columpiar libremente como spiderman
    P0312  i want it to be like avatar the last air bender and 3D and every element gets their own nation
    P0441  Lets build a 3d game that is a arcade where the user can choose from a few arcade games to play from a menu then use a first person camera from afar to be able 

  Open World & Survival RPG -> none  (8 scenes)
    P0003  Create a massive, seamless 3D Open-World RPG map divided into 4 hyper-detailed mega-biomes, connected by a central neutral hub called "The Nexus Palace".\n\nZon
    P0007  anime game with fruits like creation as a legendary ice as rare flame rare mammoth as mythic and T-Rex as mythic with different islands with different bosses an
    P0017  low graphics long storyline mobile-related Mech game at the start you are ejected from a warship down onto a planet landing in a forest the forest is named ayus

## Route shifts
top route shifts (of 285 shifted scenes):
    24                                  P0  ->  P0 + tiered
    23                                  P0  ->  P3
    22                                  P3  ->  P0
    16                                  P4  ->  P0
    16                                  P0  ->  P0 + CHECK
    15                                  P6  ->  P0
    13                                  P0  ->  P0 + P3
     8                         P0 + tiered  ->  P0
     7                                  P2  ->  P0
     6                                  P0  ->  P0 + SET

examples of top route shifts (up to 3 per transition):

  P0 -> P0 + tiered  (24 scenes)
    P0065  lets make a mech combat game, first person. use generate_mesh to generate the hud. include weapons like gatling guns, rockets, etc... generate a map / terrain. 
    P0117  make a PvP arena with detail
    P0131  hi I wana make a game wear u can dress up and go on a run way or u can go make an outfit and post it on a fake like thing

  P0 -> P3  (23 scenes)
    P0004  Build a medieval castle dungeon with stone corridors, torch lighting, and three distinct rooms. Room 1 has small skeleton enemies, Room 2 has a puzzle room with
    P0027  can you make a game where your a cat and you have to scratch furniture to get money and with the money you can buy different cat patterns that makes you stronge
    P0133  I want something that gives an option to change your outfit, kinda like catalog avatar, but it's like a place that people can socialize and make friends. as wel

  P3 -> P0  (22 scenes)
    P0047  make a game where you have a grenade launcher and you are in first person mode. you spawn in the lobby the in 1min you go to battle and then try to be last stan
    P0055  make a 3d game where you are an army soldier and your job is to damage all of the targets/robloxians and the more damages you get the more money you earn. use m
    P0107  I want to add a new map to my tactical shooter. Can you create a map that looks like Gaza?

  P4 -> P0  (16 scenes)
    P0016  create an open world 3d game about killing enemies, leveling up, increasing statsamd unlock areas. add a menu where theres a shop system, settings. add a advanc
    P0017  low graphics long storyline mobile-related Mech game at the start you are ejected from a warship down onto a planet landing in a forest the forest is named ayus
    P0116  make a pvp sniper game that has maps like nuketown a call of duty look to it with a home screen the a play arena

  P0 -> P0 + CHECK  (16 scenes)
    P0022  Create a super simple, high-quality 3D dinosaur roleplay MVP in Roblox.\n\nThe player should spawn directly as one realistic but Roblox-friendly T-Rex dinosaur.
    P0024  faça um jogo ultra realista com várias florestas e vegetações em 3D de um jogo de animais com vários animais que dá para controlar e os animais em 3D com o mapa
    P0053  We are making a game called Piggy Chomp. The game is 3D. There is a crocodile in the middle of a lake. You can shoot little cute piggies at the crocodile. If th

  P6 -> P0  (15 scenes)
    P0052  builder make my game a chasing game like forsaken till the round ends and make it 3d and add verity cause he is yellow and add creator and falsity. falsity is 🔵
    P0074  Help me create a game of tag that happens in a 3-D space I'll need some obstacles in this 3-D space some grass on the ground and maybe Wall so I don't go too fa
    P0151  make a 3D horror game called survive the rake and make the map a giant forest and it's super dark your stuck in first person and all you have is a flash light m
