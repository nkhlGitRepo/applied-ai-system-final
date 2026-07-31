# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

Give your model a short, descriptive name.  
Example: **VibeFinder 1.0**  

SoundRadar 1.0

---

## 2. Limitations and Biases

One clear limitation is that the system has 100 songs to work with. This means that the recommendations get repetitive once they have been used to answer a certain number of queries. There is also a massive popularity bias, as mainstream genres like pop have way more options than niche genres like synthwave. Another possible bias is that the binary genre matching could create a filter bubble. If you like indie, you'll mostly get the same few indie songs which is generally poor for discovery. The algorithm also fails to understand what makes a song actually resonate with people, as it only looks at a select few criteria. It looks at energy and mood, but misses things like lyrics and subtle emotional layers that a would play a large role in a person liking a given song.

## 3. Potential Misuse and Prevention

There are a few ways this system could be misused. One would be someone tampering with the song data to boost certain artists unfairly. It would also be possible for the binary genre matching to accidentally trap users in filter bubbles where they only hear one type of music. Another misuse case could involve a malicious actor spamming requests to crash the system or using injection attacks. I have guardrails in place that would stop these threats. Input validation stops SQL injection before it could cause damage. I have also included rate limiting, which caps requests at 100 per hour so spam attacks don't completely exhaust resources. A safeguard I used against possible bias or bubbles is that everything is transparent. You can always see why a song was recommended, which makes it easy to spot problems. The system is simple and readable, so any tampering would be obvious.

## 4. What Surprised Me While Testing

When doing early testing, I was surprised to find that multi phase playlists returned fewer songs than requested. When I would request 10 songs for a "sad to happy" journey, the recommender would return 7.  I discovered that this was because songs were being dropped as duplicates across phases. In order to fix it, I had to add a 30% buffer. Another surprise was that high energy requests for running were consistently returning calm songs. After some investigation, it turned out that my intent detector was ignoring energy constraints. I ended up changing the algorithmic priority order, which solved the problem. On a positive not, I was quite surprised that the majoirty of my tests passed without major issues, meaning my design was solid from the beginning.

## 5. Working with AI as a Collaborator

When collaborating with AI, I often asked for ways to make the design and algorithm more effective.  One helpful suggestion was that instead of defaulting every mood to "happy", I should map each genre to its natural mood. This meant mapping lofi to chill, jazz to relaxed, and ambient to meditative,which made the recommendations way better. AI also suggested separating the scoring logic so I could easily swap between different recommendation modes without rewriting code. But AI also made mistakes. It initially suggested training a neural network for higher accuracy, which I rejected because I needed transparency more than accuracy. More directly, when I asked for example outputs, AI created fake placeholder examples instead of actually running the system. I had to push back and ask it to execute real queries to show authentic results.

---

