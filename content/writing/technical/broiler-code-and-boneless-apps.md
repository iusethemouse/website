---
title: Broiler code and boneless apps
date: 2026-10-13
description: Reflections on vibe coding as a software engineer in late 2026.
---
TL;DR
After successfully vibe coding myself off of music streaming, I am going back to vibeless coding.

---

A few months ago, when I was in the midst of a pretty severe bout of loss of mojo, it seemed like a good idea to find a couple of well-sized projects that I could keep chipping away at over a period of time. I did  manage to find a few, one of which ended up being centred around music, ownership, vibe coding, and how it's all very very confusing.

First, a very short backstory on my relationship with music. Due to the way I am, I have very particular requirements for my listening experience. For example, while I seem to be utterly unable to memorise lyrics, listening to a song with lyrics hooks directly into my thought stream and hijacks it almost entirely. For this reason, I am very partial to instrumental music, especially when trying to focus. I also like to listen to albums top-down, in order. In movie or game soundtrack albums - the perfect source of beautiful instrumental music - there's always a couple of tracks that, for me, ruin the whole vibe of the album. So I need to disable those without fully getting rid of them. Thanks to an idea from a dear friend, I also like to document my listening experience as I go through the album - hence, I need to be able to leave notes on tracks and on albums.

With music streaming apps (besides their well-documented and highly palpable general cancerous influence on the listener, the artist, and the industry in general), I never felt like I could listen to music the way I like. Or to __my__ music, for that matter. I started feeling nostalgic for the school days when we first used the IR ports, and then Bluetooth, to syndicate niche tracks amongst each other. Those MP3 files somehow felt physical, like you found something really cool on the street and brought it home in your pocket. Sure, the artists probably didn't see a dime from us kids back then, but they sure as heck aren't seeing any dimes from Spotify now either. With increasing fondness I started thinking about the old cassette and CD players we had, the beautiful purposefulness in how we used to engage with music.

Long story short, after a brief survey of the available open source options, I decided to vibe code a bespoke music player and music library management software that had exactly the weird little features that I wanted.

Now, as any software engineer in 2026, I use LLMs at work. And while it's not especially easy, I try to maintain a healthy boundary between my personal views on LLMs and generative AI, and the views my employer expects me to have on LLMs and generative AI. There is obviously a certain amount of cognitive dissonance there, with each side occasionally bleeding into the other. And it is perhaps this cross-pollination that resulted in me feeling rather excited and sure-footed about being able to produce a piece of software that would satisfy my strict requirements and my high bar for user experience.

After all, I knew exactly how I wanted the project to be structured technically - I sketched out the architecture, I designed the UI in Figma, I defined interaction patterns, I picked the tech stack. At the end of the day, I thought, given enough time, I would easily build it myself (†). So, let's cut to the chase, put the product management hat on, and outsource the building to an agent.

Fast-forward a few weeks, and it was done. I had my own piece of software that did exactly what I wanted it to, in exactly the way I wanted it to (and more!). But the moment of deep satisfaction and contentment that I was (perhaps secretly) hoping for never arrived. The sense of fulfilment from owning the way I listen to my music never came. And it might just be a "me" problem, but I had to sit down and reflect on why the whole experience ultimately ended up feeling so hollow.

I imagine when someone builds a house, they would know its every nook and cranny, they would remember how the western wall gave them trouble, or how the floor is a bit uneven in the master bedroom, or where to look when a particular power plug is out. Or how a painter transfers wild swirls of thought and feeling into brush strokes that feel just right, and how those strokes evoke the same thoughts and feelings decades later. I am omitting the obvious comparison of someone building software by hand, because it's simply too poignant. You can probably guess that I can absolutely not say with any semblance of honesty that "I built" my music app. I don't own it, I don't know it, I wouldn't know where to even start looking if I had to fix a bug or add a feature. Just like that, I transferred the ownership of my music listening experience from one corporation to another, which amounts to feeling a level of fulfilment similar to buying a vegetarian burger from McDonalds.

There's two important bits that I want to write down here, as findings from that experience. First, that resistance is just so fundamentally important. If anything, I feel like I lost a few brain cells - so noticeable and rapid was the process of atrophy of... thinking. Loss of skill is absolutely guaranteed, loss of intuition follows soon thereafter, then goes your unique taste, your preferences, the fine details get filed down to shapeless blobs, until the sharp thoughts that used to probe the edges of your work become duller and duller, eventually failing to surface altogether. Because there was no resistance that required them in the first place anymore.

And second - the widely circulated notion that code is now cheap and expendable. Yes, it is cheap and expendable in the same sense that mass-produced chicken meat is cheap and expendable (‡). You can certainly go to the supermarket and enjoy the convenience of the availability of a neatly packaged chicken breast. You don't typically associate that with any cost besides the immediate monetary one. But it's there, it's just expertly hidden. Now, you can also enjoy the convenience of outsourcing your thinking as well. The cost is just as expertly hidden.

The truth is - I really like my music app, and I wouldn't have built it had I not had access to LLMs. Not now, and maybe not ever. But what is also true is that I kind of wish I hand't.

---

† - it is just so interesting how constant exposure to LLM-assisted coding, and lately fully agentic coding, has completely warped my intuition about project scope, and about my own capabilities. Music players and music library management software are not made by a single person within a span of weeks of stealing an hour a day after work.

‡ - see [Broiler](https://en.wikipedia.org/wiki/Broiler).
