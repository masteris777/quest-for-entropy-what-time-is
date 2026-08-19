# What Time Is — companion code

Everything the article measures, runnable from scratch.

## Run it

```
pip install numpy matplotlib
python run_all.py
```

`run_all.py` runs every experiment and checks each number the article states,
naming the sentence it is testing. `python run_all.py --quick` uses a smaller
sweep. Node.js is optional — with it, one extra check runs.

## What is in here

| file | what it does |
|---|---|
| `two_observers.py` | the world model: three processes, fifteen steps, no clock anywhere — just vector clocks |
| `sweep.py` | four thousand worlds across eight slider settings; measures how much of a world has an order, and whether two observers can ever disagree about a causal pair |
| `make_figures.py` | the article's figure — and it asserts, for every event, that comparing tallies and drawing light cones put that event in the same region |
| `page_model.js` | the model half of the interactive page, copied verbatim, so the port can be checked against it rather than trusted |

The article calls the Python a line-for-line port of the page. That is a claim,
so `run_all.py` tests it: both are run on the same seeds and slider settings, and
every count has to agree — event totals, message totals, concurrent pairs. It is
the reason `page_model.js` is in here at all.

The two numbers worth knowing: with the message slider down, about two thirds of
all event pairs have no order at all; with it up, about one in six. And across
every world generated, the number of causally related pairs that two observers
ever wrote down in opposite orders is zero.

The interactive page itself is separate and needs no code from here.

## Scope

The article's "What this does NOT claim" section is the scope fence, and it ships
with the code in `article.md`. Short version: this is an essay with a toy. The toy
has no metric, no invariant light speed and no gravity, and nothing here is a
claim about how nature is built.

## Licence

MIT for the code. The article text is © Marijus Masteika.
