# Task 1–3 study notes

Private study notes (`notes/` is in `.git/info/exclude`). These give concepts, evidence and questions. The answers are yours to write.

## Your runs

From `results/runs.csv`. Run time comes from the load test output, because the CSV does not store it. Throughput is 200 ÷ run time.

| Run | run time (s) | reviews/s | p50 | p95 | errors | pending | accuracy | large calls | cache hits |
|---|---|---|---|---|---|---|---|---|---|
| t0-large | 10.1 | 19.8 | 501 | 598 | 0 | 0 | 93.5% | 100% | 0% |
| t0-small | 0.7 | 286 | 28 | 68 | 0 | 0 | 72.5% | 0% | 0% |
| t1-before | 26.2 | 7.6 | 275 | 455 | 17 | 0 | 92.9% | 100% | 0% |
| t1-after | 9.6 | 20.8 | 388 | 1011 | 0 | 26 | 92.5% | 100% | 0% |
| t2-0.6 | 3.8 | 52.6 | 11 | 524 | 0 | 0 | 91.5% | 38% | 0% |
| t2-0.7 | 5.5 | 36.4 | 382 | 572 | 0 | 0 | 93.0% | 53% | 0% |
| t2-0.8 | 6.5 | 30.8 | 446 | 572 | 0 | 0 | 93.5% | 64% | 0% |
| t2-0.9 | 7.9 | 25.3 | 481 | 594 | 0 | 0 | 93.5% | 77% | 0% |
| t3-cache | 3.8 | 52.6 | 10 | 536 | 0 | 0 | 93.0% | 38% | 35% |

These runs replace the earlier numbers in `note/results.md`. If you quote a number, take it from this table.

**Where the extra counts come from.** Anything marked *replay* is not in `results/runs.csv`. I ran the same 200-review workload (seed 13) through both models offline, with no delay or chaos. The replay matched your runs exactly at every setting: accuracy 145, 187, 183, 186, 187 and 187 correct out of 200, and 75, 106, 128 and 154 large calls. Cite `runs.csv` as your evidence and treat the replay as an explanation.

### Three things that apply to every question

1. **Accuracy moves in steps of 0.5%.** There are 200 reviews, so one review equals 0.5%. t2-0.7 (93.0%) and t2-0.8 (93.5%) differ by **one review**. Your earlier runs differ from these by similar amounts: t1-after was 94.3% before and is 92.5% now, with the same code. Ask whether a gap is bigger than the run-to-run noise before you build an argument on it.
2. **Run time ≈ large calls ÷ 20 per second.** This holds for every run without chaos: 75 ÷ 20 = 3.75 s (measured 3.8), 106 ÷ 20 = 5.3 s (5.5), 128 ÷ 20 = 6.4 s (6.5), 154 ÷ 20 = 7.7 s (7.9), 200 ÷ 20 = 10 s (10.1).
3. **The load test is closed-loop.** It keeps 10 requests in flight (`tools/loadtest.py:65`) and sends the next only when one finishes. It never pushes a fixed arrival rate such as 40 reviews/s.

## Q0: what the large model buys and costs

**Concept.** A model choice trades several qualities at once. "More accurate but slower" names only one of the costs.

**Evidence.**

- Benefit: t0-large against t0-small is 93.5% against 72.5%, which is 187 against 145 correct, or 42 more reviews right out of 200.
- QR3 requires 90%, so check which of the two runs meets it.
- Latency: p50 501 against 28, p95 598 against 68.
- Throughput: 19.8 against 286 reviews/s. The run times are 10.1 s and 0.7 s.
- Cost: large calls 100% against 0%, and README QR4 says every large call costs money.

**Code.** The large model's service time is about 200 ms, yet p50 is 501 ms. With 10 requests in flight and a 20 calls/s limit, each request waits about 10 ÷ 20 = 0.5 s (Little's law), so most of the p50 is queueing behind `Semaphore(4)` (`inference_service/models.py:59`). Delay is simulated here (`LARGE_DELAY_MS`), but the capacity limit is what creates the queue.

**Check your draft.** It covers accuracy and latency. Does it also cover money and the capacity limit (QR4, QR5)?

## Q1.1: why p50 misleads in t1-before

**Concept.** Percentiles describe the requests they are computed over. Look at which requests those are.

**Evidence.** t1-before p50 is 275 against t0-large 501, so under chaos the system appears *faster*.

**Code, and a point about your draft.**

- `tools/loadtest.py:96` is `lat = [r["ms"] for r in ok]`. Latency is computed **only over requests that succeeded**. The 17 requests that failed at the 10 s client timeout are not in p50 or p95.
- So **p95 is misleading here too**: t1-before p95 is 455, better than t0-large's 598. Your draft names p95 as the column to trust. Look at the row again and decide which columns actually show the damage.
- Why latency drops at all: a hung call sits on one of the client's 10 slots for 10 s, so fewer requests compete for the large model at any moment. The queue gets shorter for the survivors.

## Q1.2: why 10% hanging is worse than 10% slow

**Concept.** A hung call does harm through what it holds while it waits, and that depends on where the wait happens.

**Check this against the code, because the obvious answer is wrong here.** It is tempting to say hung calls fill the 4 model slots. They do not:

```python
# inference_service/models.py:65-68
if self._rng.random() < self.hang_rate:
    await asyncio.sleep(settings.HANG_SECONDS)   # sleeps OUTSIDE the semaphore
async with self.capacity:
```

The 20 s sleep happens **before** `async with self.capacity`, so a hung call holds none of the 4 slots while hanging. Normal calls keep flowing past it, and the model stays healthy.

So what is held?

- A client slot: one of 10 in flight, for 10 s until the client gives up (`--client-timeout`, `tools/loadtest.py:134`).
- In the gateway: an open connection and a waiting coroutine, from a pool of 200 with a 60 s timeout (`gateway/app.py:12`).
- In the review service: an open connection and a waiting coroutine, from a pool of 200 with `timeout=None` (`review_service/app.py:23`).
- In the inference service: a sleeping coroutine.

**Evidence, arithmetic to redo yourself.** 17 errors × 10 s = 170 slot-seconds. 183 successes × about 0.275 s ≈ 50 slot-seconds. That is 220 slot-seconds over 10 slots ≈ 22 s, close to the 26.2 s measured. So 8.5% of requests failing took the run from 10.1 s to 26.2 s, and throughput from 19.8 to 7.6 reviews/s. Compare that with what 10% of reviews being "slow" would have cost, for example if they took 1 s.

**Think about scale.** With 10 clients the limit you hit is the client's. What happens at the gateway's 200-connection pool at 40 reviews/s, when hung calls hold connections for up to 20 s?

**Inferred from reading the code, not measured.** Nothing in `review_service/app.py` cancels when the client disconnects, so after a client gives up, the call likely carries on. The review may then be saved after the user was told it failed, and the hung call still takes a model slot and costs money when it wakes. `large_calls` is counted on entry (`inference_service/app.py:62`), before the hang.

## Q1.3: what should happen to pending reviews

**Concept.** A fallback puts the work off, so something has to pick it up later.

**Evidence.** t1-after has 26 pending, 0 errors and 174 labelled reviews. That is 13% of reviews with no label for now.

**Code.**

- `GET /reviews/pending` already exists in `review_service/app.py`, and the `classify()` docstring says what is meant to happen next.
- Read the T1–T4 table in `worksheet/task4.md` and find the topology that matches.
- `reviews = []` (`review_service/app.py:24`) is in memory, so a restart loses pending reviews. Compare that with FR4, "reviews must not be lost".
- Think about what the later job needs: retry limits, and enough capacity that it doesn't compete with live traffic.

## Q1.4: 0.1 s and 10 s timeouts

**Concept.** A timeout has to sit above normal latency and below the patience of whoever is waiting upstream.

**Evidence for the lower bound.**

- A large call sleeps for 140–260 ms even with no queue (`models.py`, `uniform(0.7, 1.3)` × 200 ms). Compare that with 0.1 s.
- Note that the timeout also covers **queue time**, not only model time, and t0-large's p50 is 501 ms. How close is 1 s to your normal p95 of 598?

**Evidence for the upper bound.**

- The client gives up at 10 s (`--client-timeout`), and QR2 says the review service waits at most 1 s. Compare with 10 s.
- t1-after shows what a short timeout buys: run time 9.6 s against 26.2 s. Use the slot-seconds arithmetic from Q1.2 to see what each hung call would cost at 10 s.

**Reading t1-after.**

- p95 is 1011, right at the timeout, because 26 of 200 (13%) are above the 95th percentile. The p95 here is really reporting the timeout value.
- `t1-after` accuracy (92.5%) is lower than t0-large (93.5%) on a different denominator (174 against 200), and your earlier run showed 94.3%. The model didn't change. Which reviews happened to go pending did.
- 26 pending against 17 errors may be chance or queue timeouts. The hang is a 10% random draw, about 20 ± 4 expected, and these runs start from different RNG states. Your data can't separate those two explanations.

## Q2.1: which threshold

**Concept.** A threshold is a dial between cost and accuracy. Pick against the requirements, QR3 and QR4 in particular: "as few large calls as possible without breaking QR3".

**Evidence.**

| threshold | correct / 200 | large calls (replay) | p50 | p95 | throughput |
|---|---|---|---|---|---|
| 0.6 | 183 | 75 | 11 | 524 | 52.6/s |
| 0.7 | 186 | 106 | 382 | 572 | 36.4/s |
| 0.8 | 187 | 128 | 446 | 572 | 30.8/s |
| 0.9 | 187 | 154 | 481 | 594 | 25.3/s |
| large only | 187 | 200 | 501 | 598 | 19.8/s |

**Questions to work through.**

- Which rows meet QR3 at 90%? How much margin does each have, counting noise?
- What does going from 0.8 to 0.9 buy? What does going from 0.6 to 0.7 cost, and buy?
- Which step changes p50 sharply, and why there? (See Q2.2.)
- Task 3 and your t3-cache run used 0.7 as the task instructed. That doesn't have to be the threshold you choose here. If yours differs, say so.
- Name the quality given up, and be specific about what happens to it.

## Q2.2: why p50 improves much more than p95

**Concept.** Cascade makes latency **bimodal**. Requests take a fast path (about 10 ms) or a slow path (about 500 ms). A percentile falls on one path or the other, and rarely between them.

**Evidence.**

- Where the median falls depends on whether under 50% of requests escalate. At 0.6, 38% do, so the median request is fast: p50 11. At 0.7, 53% do, so it is slow: p50 382. That step sits between two adjacent thresholds.
- p95 stays at 524–594 across every threshold, and t0-large is 598. If at least 5% of requests take the slow path, p95 is a slow-path number.
- The question assumes p50 improves a lot. **Check that for your own threshold**: it is true at 0.6, but at 0.7 p50 only moves from 501 to 382.

**Code.** The slow path still passes through the same `Semaphore(4)`. Cascade reduces how many requests get there, and it doesn't make any one of them quicker.

## Q2.3: when the small model's confidence shouldn't be trusted

**Concept.** Confidence is the model's own estimate. A model can be sure and wrong, especially on inputs it can't represent. Calibration asks whether a stated 0.9 is right 90% of the time.

**Evidence (replay), at threshold 0.7.** The small model answered 94 reviews on its own and got 6 wrong, with these examples:

| Text | True label | Small said | Confidence |
|---|---|---|---|
| "Honestly the salad is not cold." | positive | negative | 0.702 |
| "Great, the noodle soup was soggy again." | positive | negative | 0.827 |
| "Excellent som tam, the staff were friendly." | negative | positive | 0.947 |
| "Perfect basil pork, the rider was polite." | negative | positive | 0.898 |

**Read these critically.**

- The first is the README's known weakness, negation. The small model only has 100 single words, so it can't see "not cold" as a phrase (`SmallModel` in `models.py`).
- The other three look like **wrong labels in the data**. `data/make_data.py` adds sarcasm and about 4% label noise on purpose (docstring, and lines 64 and 83). Think about whether each is a real model failure before citing it.
- Better examples may be ones you can argue from the model's structure: what can a 100-word bag of words never represent?

**Effect on users.** Think through who sees a wrong label, and what the cascade does differently here: no second opinion is requested, so the error is silent.

## Q3.1: which reviews benefit from the cache

**Concept.** A cache only pays off on repeats, so its value comes from the workload rather than from the cache code.

**Evidence.**

- t3-cache against t2-0.7, same threshold: large calls 53% to 38%, cache hits 35%, accuracy unchanged at 93.0%, run time 5.5 s to 3.8 s.
- p50 drops from 382 to 10, the same median effect as in Q2.2: fewer than half the requests now reach the large model. p95 hardly moves, 572 to 536.

**Code and workload.**

- `tools/loadtest.py` `workload()`: "75% unique reviews, 25% common short ones". The replay drew 56 of the 8 `FREQUENT` phrases, and 125 distinct keys overall, so at most 75 hits were possible. You got 70.
- Why 70 and not 75: there were 130 misses for 125 distinct texts. `predict()` checks the cache at `inference_service/app.py:78` and only fills it after the model answers, at line 84. Two identical reviews in flight at once both miss, which is a small cache stampede.
- Hits don't save large calls evenly. Only reviews that would have escalated save one. At 0.7, 'Delicious!', 'Too salty' and 'Cold food' fall below the threshold (20 draws in the replay). 'Late again' at 0.977 never escalates, so a hit there saves only a small-model call.
- Read `key()`: what counts as the same review? Is "Delicious!" the same as "Delicious"? What would have to be true of a long, personal review for it ever to hit?
- 35% depends on your synthetic 25/75 mix. Would real reviews repeat as much?

## Q3.2: a new model and the cache

**Concept.** A cached prediction is derived data, and it depends on the model that produced it. This is cache invalidation.

**Code.**

- `key()` uses the text only. It doesn't include the model or its version, so old answers would keep being served after a deployment, and `model` is overwritten with `"cache"` (`inference_service/app.py`, `predict()`), which hides which model made them.
- Here `reset()` happens to create a new cache (`app.py:28-30`) and the cache is in memory, so a restart empties it. Would that hold if the cache moved to a shared store such as Redis?
- The same staleness applies to a **threshold** change: entries came from whichever model answered under the old threshold. The key doesn't record that either.
- Options to weigh: flushing on deploy, versioning the key, TTL. For each, think about what happens to large-model load right after a flush, when every popular review misses at once, given the 20 calls/s limit.

## Q4: something the lecture did not cover

This one has to be yours. Places in your data worth a look, without assuming any of them is your answer:

- Under chaos, latency percentiles improved while the system got worse (t1-before against t0-large).
- Run time is almost entirely explained by large calls ÷ 20.
- p50 jumped from 11 to 382 between adjacent thresholds, while p95 barely moved.
- Adjacent thresholds can differ by a single review.
- Hit rate was limited by concurrent duplicates and by the workload mix, not by cache size.
- The same code gave t1-after accuracy of 94.3% in one run and 92.5% in another.
