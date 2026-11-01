# Task 4 study notes

Private study notes (`notes/` is in `.git/info/exclude`). They lay out the trade-offs and arithmetic. The scenario choice, design and ADR are yours.

## Which scenarios you may take

Your student ID is 6970148821. The last digit is **1**, which is odd, so you may take **A (Owner alerts) or B (Canteen kiosk)**. Scenario C is not available to you.

## Capacity arithmetic

**The rule.** Large calls per second at peak = peak reviews/s × large_calls share. It must stay under the 20 calls/s limit (4 at once ÷ about 0.2 s).

Only Scenario A gives a peak: 40 reviews/s. The worksheet requires this arithmetic for A.

| Run | large_calls | exact count (replay) | × 40 reviews/s | vs 20 calls/s | utilisation | measured throughput |
|---|---|---|---|---|---|---|
| t0-large | 100% | 200/200 | 40.0 | over | 200% | 19.8/s |
| t2-0.9 | 77% | 154/200 | 30.8 | over | 154% | 25.3/s |
| t2-0.8 | 64% | 128/200 | 25.6 | over | 128% | 30.8/s |
| t2-0.7 | 53% | 106/200 | 21.2 | over, slightly | 106% | 36.4/s |
| t2-0.6 | 38% | 75/200 | 15.0 | under | 75% | 52.6/s |
| t3-cache (0.7 + cache) | 38% | 75/200 | 15.0 | under | 75% | 52.6/s |

Measured throughput gives you a second, independent check: only the last two rows reached 40 reviews/s, the same conclusion as the arithmetic.

**Use the rounded `large_calls` from `runs.csv` in the worksheet** (38% × 40 = 15.2 calls/s). The exact 75/200 gives 15.0. Either is fine if you say which you used.

**Limits of this arithmetic. Think about them before you lean on it.**

- *Utilisation is not headroom.* Queues grow quickly as utilisation nears 100%. Under the limit doesn't mean latency stays low, and 75% is an average that a burst can exceed.
- *Over the limit means unbounded queueing.* At 21.2 against 20 calls/s, the excess of 1.2 calls/s adds up to 72 queued calls per minute of sustained peak. Divide a queue length by 20/s to get the wait, then compare it with your 2 s deadline.
- *Your p95 values were not measured at 40 reviews/s.* The load test is closed-loop at 10 in flight, so no run tested a sustained arrival rate. You can say so as a limit of your evidence.
- *t3-cache's 38% depends on the 25% repeat mix*, on a cold cache and on 200 requests. If real reviews repeat less, which row do you fall back to? t2-0.7's 21.2 calls/s is what you'd need with a 0% hit rate at that threshold.
- *Chaos runs are separate.* The t2 and t3 runs had no hang. No run has combined cascade with `--hang-rate`. `t1-after` used the large strategy only.

## Scenario A: Owner alerts

**What it demands:** a push within 2 s, 40 reviews/s at peak, missed alerts acceptable, wrong alerts corrode trust.

**A measurement gap.** The scenario's key quality is whether a *negative* label is right when it fires, which is **precision on negatives**. `runs.csv` only reports overall accuracy, which treats both error types alike. The replay gives these numbers. They are not in `runs.csv`, so if you use them, say they come from an offline replay of the same workload.

| Setting | accuracy | negative precision | false alerts in 200 | missed negatives (of 109) | large calls |
|---|---|---|---|---|---|
| small only | 72.5% | 75.0% (81/108) | 27 | 28 | 0 |
| cascade 0.6 | 91.5% | 91.1% (102/112) | 10 | 7 | 75 |
| cascade 0.7 | 93.0% | 94.4% (101/107) | 6 | 8 | 106 |
| cascade 0.8 | 93.5% | 95.3% (101/106) | 5 | 8 | 128 |
| large only | 93.5% | 95.3% (101/106) | 5 | 8 | 200 |

Note the tension: the settings with the fewest false alerts are the ones over capacity. Bringing t3-cache in means asking what the cache does to precision. Its answers came from the same models, and accuracy stayed at 93.0%.

**Trade-offs.**

| Topology | For Scenario A | Against, or watch for |
|---|---|---|
| **T1** sync service | Simple, today's design. Every alert comes from the service, with a single place to change models. | All-large is 40 calls/s, double the limit. It needs cascade or cache plus a guard. Latency depends on the network and the queue. |
| **T2** library | No network call. Fast, and t0-small's 68 ms p95 and 286 reviews/s are comfortable. | The small model on its own gives 75% negative precision in the replay, 27 false alerts per 200. That is the failure the scenario warns about. The large model can't run here within the capacity limit. |
| **T3** hybrid | Answers confident reviews locally, and spends large capacity on the hard ones. Reduces load on inference. | Two places to deploy models, so version drift. The threshold now sits in a business service. Escalated reviews still queue for the 4 slots, so the arithmetic above still applies. |
| **T4** async/batch | A queue absorbs a peak above 20 calls/s. | Time in the queue counts toward the 2 s. How long can a queue get before the deadline fails? What does a batch do to "within 2 seconds"? |

**Questions to resolve.**

- "A missed alert is acceptable": what should happen when a review is pending, or the small model is unsure and large is busy? `t1-after` shows 26 of 200 pending under chaos, and those are reviews with no alert.
- A fallback that gives no label loses an alert. Does that break the scenario's rule, or fit it?
- `INFERENCE_TIMEOUT_S` is 1 s and the deadline is 2 s. What else must fit in the second that remains, including the push?
- Could you treat escalation asymmetrically, based on which errors matter? For instance, does a confident *positive* need the same scrutiny as a confident *negative*?
- Should the alert use a different threshold from the label? That is a design choice you'd have to defend.

## Scenario B: Canteen kiosk

**What it demands:** tablets offline for minutes, several times a day, accept **every** review, and labels by end of day. No real-time label is required.

**Which numbers matter.** The capacity peak doesn't apply here, since no arrival rate is given. Your own question: how many reviews a day would stress 20 calls/s? That limit is 72,000 calls/hour. How would you size a nightly job, and how many hours does your estimated volume need?

**Evidence that transfers.**

- `t0-small`: 72.5% accuracy, 0 large calls, 68 ms p95. Compare with QR3's 90%: is a kiosk-side label alone good enough, or only useful as a provisional one?
- t2 runs: cascade reduces large calls to 38–77% at 91.5–93.5% accuracy, so it can cut batch cost too. Latency matters little here, so read p50 and p95 differently than in A.
- t3-cache: 35% hits and 38% large calls with a 25% repeat mix. Kiosk reviews are short, so repeats might be more common. That's a hypothesis your runs don't test.
- `t1-after`: 0 errors, 26 pending shows the save-now-label-later shape. A kiosk offline is the same idea on the far side of the network.

**Trade-offs.**

| Topology | For Scenario B | Against, or watch for |
|---|---|---|
| **T1** sync service | Simple, one accurate result per review. | The tablet can't reach it when offline. Without local storage, a review written offline fails the "accept every review" rule. |
| **T2** library, on device | Works offline and gives an immediate label. | t0-small's 72.5% is under QR3's 90%. Updating models across many tablets. A large model can't run on a tablet. |
| **T3** hybrid | Small on tablet, large when online. Uses the network when it's there. | Unsure reviews during an outage need somewhere to wait, so you need a local queue regardless. More moving parts than the labelling deadline asks for? |
| **T4** async/batch | Fits an end-of-day deadline and off-peak scoring. Queues naturally absorb outages. | Owners see no label until the batch runs. The queue must survive a restart. Note the in-memory `reviews = []` in `review_service/app.py:24` won't do. |

**Questions to resolve.**

- Where exactly does a review live during an outage? "Accept" has to mean durable storage on the tablet. What if the tablet reboots or is damaged?
- Upload after reconnect can retry. How do you avoid duplicates when a send succeeded but its acknowledgement was lost? Think about idempotency keys.
- What if many tablets reconnect at once?
- What happens to a review the batch job fails on, or one still unlabelled near the deadline?
- Does the tablet need the small model at all if nothing needs a label until end of day? Show your reasoning either way.

## Good evidence for the worksheet table

- Cite run names from `results/runs.csv`, as the worksheet asks.
- Choose runs that test your actual design. If no run covers it, such as a batch job or cascade under chaos, say so rather than stretching a number.
- Accuracy gaps of one or two reviews (0.5–1%) aren't strong evidence by themselves.
- Your ADR's "Alternatives considered" is stronger if a rejected topology is rejected on one of your numbers.
