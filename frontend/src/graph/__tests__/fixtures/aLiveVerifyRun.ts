/**
 * One live Verify run, kept whole: the six-claim Hormuz map Kent's own key paid
 * for on 2026-09-21, and the map he was looking at when he said the boxes were
 * "a little chaotic and hard to read".
 *
 * **What it is.** The `events` array of the working file that run left behind —
 * `backend/.runs/hormuz-2026-09-21T18-24-54Z-01M32HVA1F3SX18H513M6GTNPT.json`,
 * written by the run itself and edited by nobody. Sixteen events: the run
 * starts, eleven proposals are accepted, one is refused, the Verify door gives
 * its verdict, the receipt arrives and the run stops. Six claims, nine arrows.
 * Nothing inside an event was stripped, shortened or rounded. The only thing
 * added is each event's own name, which on the wire is the `event:` line beside
 * the `data:` line and which the kept file does not repeat.
 *
 * **It is an input to a test and nothing else.** It is not a recording: it is
 * not under `backend/recordings/`, no launchpad card reaches it, and nothing
 * ever replays it to a reader. The rest of the kept file — the transcript, the
 * receipt's working, the finished graph — was left out, because a test of where
 * a tile goes reads none of it.
 *
 * **It cost nothing to add.** The run was already made and already paid for
 * ($2.17, 2026-09-21). Nothing here asks a model anything.
 *
 * **Why this run and not the committed recording.** The defect decision record
 * 0024 is about exists only on a map made through the **Verify** door, where the
 * destination claim arrives second with nothing pointing at it yet. On this run
 * it lands in the leftmost column, gains four arrows over the next ten events,
 * and ends three columns to the right of where it was drawn — so three of the
 * run's nine arrows were drawn pointing backwards. The one stream this
 * repository already holds, `backend/recordings/hormuz.jsonl`, is an Explore run
 * with no destination and no backwards arrow, so on it the defect is invisible.
 *
 * See `README.md` beside this file.
 */

import type { StreamEvent } from "../../../stream/events";

/** The run, event by event, in the order they came off the wire. */
export const A_LIVE_VERIFY_RUN: readonly StreamEvent[] = [
  {
    event: "generation_started",
    generation_id: "01M32HVA1F3SX18H513M6GTNPT",
    seed: 20261001,
    hypothesis: "The Strait of Hormuz is going to open next week.",
    target: "Brent crude settles below $68 for five sessions.",
  },
  {
    event: "proposal_accepted",
    at: 0,
    proposition: {
      id: "01M32HZYPTKVEGND75JWG353AC",
      claim:
        "The Strait of Hormuz reopens to commercial shipping traffic during the week of 28 September to 4 October 2026.",
      kind: "hypothesis",
      resolution: {
        criteria:
          "IMF PortWatch's Strait of Hormuz vessel-transit count (published in the IMF PortWatch Global Transport Tracker, the dataset cited throughout the current crisis by Reuters, gCaptain and the Straits Daily Brief) records an average of at least 40 vessel transits per day \\u2014 roughly half of the approximately 85-per-day pre-crisis baseline \\u2014 sustained over at least three separate days falling between 21 September 2026 and 4 October 2026 inclusive.",
        source: "IMF PortWatch (Global Transport Tracker)",
        by: "2026-10-04",
      },
      prior: {
        p: 0.07,
        lo: 0.03,
        hi: 0.15,
        owner: "model",
      },
      beliefs: {
        model: {
          p: 0.07,
          lo: 0.03,
          hi: 0.15,
          owner: "model",
        },
        user: null,
        market: null,
      },
      base_rate: {
        reference_class:
          "Calendar weeks of the current Strait of Hormuz crisis, counted from the start of the effective closure on 2 March 2026 through 20 September 2026 (about 29 weeks), where a week counts as a 'reopening week' if vessel-transit volumes rose from near-zero toward the pre-crisis baseline within that week (as happened briefly around 17 April 2026 and again around 17-19 June 2026, per CSIS and Al Jazeera reporting, before Iran re-closed the strait each time)",
        k: 2,
        n: 29,
        sources: [
          "https://www.csis.org/analysis/strait-hormuz-8-charts",
          "https://www.aljazeera.com/news/2026/6/11/iran-shuts-hormuz-strait-but-wasnt-it-already-closed",
          "https://www.aljazeera.com/news/2026/7/9/strait-of-hormuz-what-has-happened-since-the-us-iran-mou-on-june-17",
        ],
      },
      evidence: [],
      payoff: null,
      not_tradeable_reason: null,
    },
    links: [],
    frontier: ["01M32HZYPTKVEGND75JWG353AC"],
  },
  {
    event: "proposal_accepted",
    at: 1,
    proposition: {
      id: "01M32J8Q6FB1PPJ64XC5ECAPPS",
      claim:
        "Brent crude oil settles below $68.00 per barrel for five consecutive trading sessions",
      kind: "event",
      resolution: {
        criteria:
          "The daily settlement price of the ICE Brent Crude futures front-month contract closes below $68.00 per barrel on five consecutive trading sessions, on or before the by-date",
        source:
          "ICE Futures Europe (Intercontinental Exchange) Brent Crude futures daily settlement prices",
        by: "2027-03-31",
      },
      prior: {
        p: 0.08,
        lo: 0.03,
        hi: 0.18,
        owner: "model",
      },
      beliefs: {
        model: {
          p: 0.08,
          lo: 0.03,
          hi: 0.18,
          owner: "model",
        },
        user: null,
        market: null,
      },
      base_rate: {
        reference_class:
          "Calendar years 2015 through 2025 in which Brent crude's ICE front-month daily settlement price fell below $68/barrel for at least one multi-session stretch at some point during the year, per worldoilmonitor.com's year-by-year annual average/high/low series and corroborating EIA and Wikipedia oil-market-chronology reporting (2015-16 crash to the $20s-$40s, 2017-19 range of roughly $50-$80, the 2020 COVID collapse, the 2021 recovery starting near $50, and the 2025 slide to a $63 December average that continued into a sub-$68 opening week of January 2026)",
        k: 8,
        n: 11,
        sources: [
          "https://worldoilmonitor.com/brent-price-history",
          "https://www.eia.gov/todayinenergy/detail.php?id=66944",
          "https://en.wikipedia.org/wiki/2026%E2%80%932028_world_oil_market_chronology",
          "https://brentchart.com/brent-price-history",
        ],
      },
      evidence: [],
      payoff: null,
      not_tradeable_reason: null,
    },
    links: [],
    frontier: ["01M32HZYPTKVEGND75JWG353AC"],
  },
  {
    event: "proposal_accepted",
    at: 2,
    proposition: {
      id: "01M32JNTXX3D1ZMGWXDSP5B7ZC",
      claim:
        "Crude oil tanker transits through the Strait of Hormuz return to at least 80 percent of their average daily volume recorded in January 2026, the last full month before the closure that began in late February 2026.",
      kind: "event",
      resolution: {
        criteria:
          "The average daily number of crude oil tanker transits through the Strait of Hormuz, as tracked in Kpler or Lloyd's List Intelligence ship-tracking data, over any consecutive seven-day period reaches at least 80 percent of the average daily transit count recorded in January 2026.",
        source: "Kpler / Lloyd's List Intelligence tanker-tracking data",
        by: "2026-11-03",
      },
      prior: {
        p: 0.13,
        lo: 0.05,
        hi: 0.27,
        owner: "model",
      },
      beliefs: {
        model: {
          p: 0.13,
          lo: 0.05,
          hi: 0.27,
          owner: "model",
        },
        user: null,
        market: null,
      },
      base_rate: {
        reference_class:
          "Weekly Strait of Hormuz vessel-transit counts reported by USNI News and Lloyd's List Intelligence for each week between the 17 June 2026 Iran-US ceasefire MoU and the week ending 28 August 2026, counting a week as a success if transits reached at least 80 percent of the pre-28 February 2026 weekly average",
        k: 0,
        n: 10,
        sources: [
          "https://news.usni.org/2026/08/28/strait-of-hormuz-tanker-transits-up-but-still-below-pre-war-levels",
          "https://www.aljazeera.com/news/2026/8/27/how-a-95-percent-drop-in-hormuz-traffic-changed-global-shipping",
        ],
      },
      evidence: [],
      payoff: null,
      not_tradeable_reason: null,
    },
    links: [
      {
        id: "01M32JNTXX3D1ZMGWXDSP5B7ZD",
        source: "01M32HZYPTKVEGND75JWG353AC",
        target: "01M32JNTXX3D1ZMGWXDSP5B7ZC",
        mode: "sustain",
        strength: 1.7,
        lag: 30.0,
        shape: "ramp",
        half_life: null,
        rationale:
          "Once the Strait is legally and physically reopened, shipowners, charterers and war-risk insurers can resume routing tankers through it without breaching a declared closure, so transit volumes climb over the following weeks; but the same conflict's earlier ceasefire (17 June 2026) showed that formal reopenings translate into traffic only gradually, with volumes still far below pre-war levels months later, so the push is a slow ramp rather than an instant jump, and it needs the strait to stay open to keep building.",
        sources: [
          {
            url: "https://news.usni.org/2026/08/28/strait-of-hormuz-tanker-transits-up-but-still-below-pre-war-levels",
            title: "Strait of Hormuz Tanker Transits Up But Still Below Pre–War Levels - USNI News",
            retrieved: "2026-09-21",
          },
          {
            url: "https://discoveryalert.com/strait-hormuz-oil-tanker-traffic-resuming-price-trends/",
            title: "Strait of Hormuz Oil Tanker Traffic Resuming in 2026: Key Insights",
            retrieved: "2026-09-21",
          },
        ],
        provenance: "documented",
        reflexive: false,
      },
    ],
    frontier: ["01M32HZYPTKVEGND75JWG353AC", "01M32JNTXX3D1ZMGWXDSP5B7ZC"],
  },
  {
    event: "proposal_accepted",
    at: 3,
    proposition: null,
    links: [
      {
        id: "01M32JT53C8DQ0SH0GTK83EJ8K",
        source: "01M32JNTXX3D1ZMGWXDSP5B7ZC",
        target: "01M32J8Q6FB1PPJ64XC5ECAPPS",
        mode: "sustain",
        strength: 0.9,
        lag: 3.0,
        shape: "ramp",
        half_life: null,
        rationale:
          "When physical tanker flow through Hormuz actually returns to normal, it puts roughly 15-16 million barrels a day of real supply back into a market that had already built a 2-4 million bpd global surplus from non-Hormuz growth (US shale, Brazil, Guyana) plus OPEC+ quota hikes made during the closure to compensate; once the bottleneck clears that surplus is no longer masked. News-driven Hormuz reopening announcements have already produced single-day Brent drops of 9-11 percent in this crisis, and forecasters (JPMorgan, ADI Analytics) see Brent settling into the high-$70s to $60s once the disruption fully unwinds, so a confirmed, sustained recovery of actual transit volumes is what turns a partial risk-premium unwind into a deeper, several-day slide under $68. Because the added barrels only exist while transits stay near normal, the depressive push would fade if flows fell back.",
        sources: [
          {
            url: "https://adi-analytics.com/2026/04/16/why-oil-is-likely-to-fall-back-into-the-60s-by-end-2026/",
            title: "Why oil is likely to fall back into the $60s by end‑2026",
            retrieved: "2026-09-21",
          },
          {
            url: "https://www.jpmorgan.com/insights/global-research/commodities/oil-prices",
            title: "Oil Prices Forecast | J.P. Morgan Global Research",
            retrieved: "2026-09-21",
          },
          {
            url: "https://www.nbcnews.com/business/markets/oil-prices-plunge-stocks-jump-hormuz-open-iran-war-rcna332321",
            title:
              "Oil prices plunge 11% after Iran says Strait of Hormuz is open for commercial vessels",
            retrieved: "2026-09-21",
          },
          {
            url: "https://oilprice.com/Latest-Energy-News/World-News/Oil-Prices-Plunge-as-US-and-Iran-Reach-Deal-to-Reopen-Strait-of-Hormuz.html",
            title:
              "Oil Prices Plunge as U.S. and Iran Reach Deal to Reopen Strait of Hormuz | OilPrice.com",
            retrieved: "2026-09-21",
          },
        ],
        provenance: "documented",
        reflexive: false,
      },
    ],
    frontier: ["01M32HZYPTKVEGND75JWG353AC", "01M32JNTXX3D1ZMGWXDSP5B7ZC"],
  },
  {
    event: "proposal_accepted",
    at: 4,
    proposition: {
      id: "01M32JV3X5Q6GFHTP5C6TT6CXE",
      claim:
        "The International Energy Agency's monthly Oil Market Report shows the global crude oil supply-demand balance back in a surplus of at least 1.0 million barrels per day.",
      kind: "event",
      resolution: {
        criteria:
          "In the first Oil Market Report edition covering a month that falls after the Strait of Hormuz tanker-transit recovery is confirmed, the IEA states that global oil supply exceeds global oil demand by at least 1.0 million barrels per day, moving the market back toward the roughly 3.7 mb/d surplus it was running before the war-related closure began in late February 2026.",
        source: "International Energy Agency, Oil Market Report",
        by: "2026-12-31",
      },
      prior: {
        p: 0.45,
        lo: 0.25,
        hi: 0.65,
        owner: "model",
      },
      beliefs: {
        model: {
          p: 0.45,
          lo: 0.25,
          hi: 0.65,
          owner: "model",
        },
        user: null,
        market: null,
      },
      base_rate: null,
      evidence: [],
      payoff: null,
      not_tradeable_reason: null,
    },
    links: [
      {
        id: "01M32JV3X5Q6GFHTP5C6TT6CXF",
        source: "01M32JNTXX3D1ZMGWXDSP5B7ZC",
        target: "01M32JV3X5Q6GFHTP5C6TT6CXE",
        mode: "sustain",
        strength: 1.2,
        lag: 30.0,
        shape: "ramp",
        half_life: null,
        rationale:
          "Restoring tanker transits to 80% of the January 2026 baseline puts on the order of 15-16 mb/d of Gulf crude back into the water, reversing most of the shortfall that has forced record inventory draws and emergency SPR releases since the closure; the IEA needs roughly a reporting cycle to fold the restored flows into its monthly global balance. The push only holds while transits stay near that 80% level, because the surplus is the arithmetic result of supply running ahead of demand, not a one-off event.",
        sources: [
          {
            url: "https://www.iea.org/commentaries/how-global-oil-supplies-have-readjusted-to-help-fill-the-huge-gap-left-by-the-strait-of-hormuz-shock",
            title:
              "How global oil supplies have readjusted to help fill the huge gap left by the Strait of Hormuz shock – Analysis - IEA",
            retrieved: "2026-09-21",
          },
          {
            url: "https://finance.yahoo.com/energy/articles/iea-slashes-2026-oil-supply-121827050.html",
            title: "IEA slashes 2026 oil supply forecast as Hormuz closure deepens",
            retrieved: "2026-09-21",
          },
        ],
        provenance: "documented",
        reflexive: false,
      },
    ],
    frontier: [
      "01M32HZYPTKVEGND75JWG353AC",
      "01M32JNTXX3D1ZMGWXDSP5B7ZC",
      "01M32JV3X5Q6GFHTP5C6TT6CXE",
    ],
  },
  {
    event: "proposal_accepted",
    at: 5,
    proposition: null,
    links: [
      {
        id: "01M32K1YYMBV7W3RX6S6TJYJPE",
        source: "01M32HZYPTKVEGND75JWG353AC",
        target: "01M32J8Q6FB1PPJ64XC5ECAPPS",
        mode: "sustain",
        strength: 0.45,
        lag: 2.0,
        shape: "ramp",
        half_life: null,
        rationale:
          "Reopening removes the acute war-risk insurance and geopolitical risk premium currently embedded in Brent, which as of 18-21 September 2026 was trading near $103-104, roughly 55% above year-ago levels, almost entirely on Hormuz-conflict fear. Traders have been burned before by premature 'reopening' reports that reversed (Iran's disputed closures, contested re-openings, attacks 'denting hopes'), so the market is likely to price out the premium over a few days of confirmation rather than instantly, and this component of the effect only holds while the strait stays open \"",
        sources: [],
        provenance: "argued",
        reflexive: false,
      },
    ],
    frontier: [
      "01M32HZYPTKVEGND75JWG353AC",
      "01M32JNTXX3D1ZMGWXDSP5B7ZC",
      "01M32JV3X5Q6GFHTP5C6TT6CXE",
    ],
  },
  {
    event: "proposal_accepted",
    at: 6,
    proposition: null,
    links: [
      {
        id: "01M32JXNYF675H289RS9QBZDX1",
        source: "01M32JV3X5Q6GFHTP5C6TT6CXE",
        target: "01M32J8Q6FB1PPJ64XC5ECAPPS",
        mode: "sustain",
        strength: 1.0,
        lag: 3.0,
        shape: "step",
        half_life: null,
        rationale:
          "An IEA report confirming the global balance has swung to a surplus of at least 1.0 mb/d is the fundamental data confirmation that traders wait for before pressing a bearish view for a sustained stretch rather than a single session; IEA's own July 2026 report already frames the expected swing back to surplus as hinging on exactly this Strait tanker-flow recovery, so its publication would validate and reinforce the price pressure the physical flow recovery has already started. Historically, confirmed multi-year gluts of comparable size (the 1998 Asian-crisis glut, the 2014-2016 US shale glut, the 2020 demand-collapse glut) were each followed by prolonged, not one-day, price weakness, which is why the push is modeled as holding rather than spiking. The push is a 'sustain' rather than a 'trigger' because if a subsequent report revised the surplus away, the extra downward pressure from this arrow would lift, even though the tanker-flow-driven pressure on the other arrow would remain.",
        sources: [
          {
            url: "https://www.iea.org/reports/oil-market-report-july-2026",
            title: "Oil Market Report - July 2026 – Analysis - IEA",
            retrieved: "2026-09-21",
          },
          {
            url: "https://www.eia.gov/todayinenergy/detail.php?id=24432",
            title:
              "Crude oil prices started 2015 relatively low, ended the year lower - U.S. Energy Information Administration (EIA)",
            retrieved: "2026-09-21",
          },
          {
            url: "https://en.wikipedia.org/wiki/2010s_oil_glut",
            title: "2010s oil glut",
            retrieved: "2026-09-21",
          },
        ],
        provenance: "documented",
        reflexive: false,
      },
    ],
    frontier: [
      "01M32HZYPTKVEGND75JWG353AC",
      "01M32JNTXX3D1ZMGWXDSP5B7ZC",
      "01M32JV3X5Q6GFHTP5C6TT6CXE",
    ],
  },
  {
    event: "proposal_rejected",
    at: 7,
    claim_in_words: "This arrow, on the map as it stood once the rest of its round had landed.",
    violations: [
      {
        code: "duplicate_link",
        subject: "01M32JWHREJQFP2D6Z7K9TWB12",
        message:
          '"The International Energy Agency\'s monthly Oil Market Report shows the global cr…" and "Brent crude oil settles below $68.00 per barrel for five consecutive trading se…" are already joined by an arrow in that direction. Two arrows the same way round add their pushes together, so a second one says the cause is stronger than either arrow claims.',
      },
    ],
    frontier: [
      "01M32HZYPTKVEGND75JWG353AC",
      "01M32JNTXX3D1ZMGWXDSP5B7ZC",
      "01M32JV3X5Q6GFHTP5C6TT6CXE",
    ],
  },
  {
    event: "proposal_accepted",
    at: 8,
    proposition: {
      id: "01M32K63YVGYPVQN443GE8T4JB",
      claim:
        "OPEC+ approves a further increase to its collective crude oil production quotas at a ministerial or Joint Ministerial Monitoring Committee meeting, marking at least a sixth consecutive monthly output increase since the Strait of Hormuz closure began in February 2026.",
      kind: "event",
      resolution: {
        criteria:
          "OPEC's own press release or statement following a ministerial or JMMC meeting announces an increase (not a cut, pause, or rollover) in collective output quotas for the following month, continuing the unbroken monthly-increase streak that began in April 2026.",
        source: "OPEC Secretariat (opec.org press releases)",
        by: "2026-10-31",
      },
      prior: {
        p: 0.72,
        lo: 0.5,
        hi: 0.88,
        owner: "model",
      },
      beliefs: {
        model: {
          p: 0.72,
          lo: 0.5,
          hi: 0.88,
          owner: "model",
        },
        user: null,
        market: null,
      },
      base_rate: {
        reference_class:
          "OPEC+ ministerial/JMMC meetings held monthly from April through August 2026, after the Strait of Hormuz closure began, where the group decided whether to raise, hold, or cut collective output quotas",
        k: 5,
        n: 5,
        sources: [
          "https://www.cnbc.com/2026/06/07/opec-set-for-fourth-oil-quota-hike-since-strait-of-hormuz-closure.html",
          "https://www.cnbc.com/2026/07/05/opec-set-to-approve-another-oil-output-increase.html",
          "https://vision2030.ai/analysis/opec-august-2026-output-increase/",
        ],
      },
      evidence: [],
      payoff: null,
      not_tradeable_reason: null,
    },
    links: [
      {
        id: "01M32K63YVGYPVQN443GE8T4JC",
        source: "01M32HZYPTKVEGND75JWG353AC",
        target: "01M32K63YVGYPVQN443GE8T4JB",
        mode: "trigger",
        strength: 0.55,
        lag: 5.0,
        shape: "step",
        half_life: null,
        rationale:
          "A confirmed reopening removes the physical shipping constraint that had capped how much of any new OPEC+ quota could actually reach buyers, so producers who had kept raising quotas through the closure to recapture lost market share now have both the political cover and the logistical confidence to keep doing so. It also strengthens the case of members like Saudi Arabia who have pushed for market-share recovery over price defense, since the crisis-management argument for restraint disappears once the strait is open.",
        sources: [],
        provenance: "argued",
        reflexive: false,
      },
    ],
    frontier: [
      "01M32JNTXX3D1ZMGWXDSP5B7ZC",
      "01M32JV3X5Q6GFHTP5C6TT6CXE",
      "01M32K63YVGYPVQN443GE8T4JB",
    ],
  },
  {
    event: "proposal_accepted",
    at: 9,
    proposition: null,
    links: [
      {
        id: "01M32K7MJ0MVT1Q59MCXQNWZPA",
        source: "01M32K63YVGYPVQN443GE8T4JB",
        target: "01M32JV3X5Q6GFHTP5C6TT6CXE",
        mode: "trigger",
        strength: 1.3,
        lag: 30.0,
        shape: "ramp",
        half_life: null,
        rationale:
          "Each OPEC+ quota increase adds physical barrels of crude to global supply over the following weeks as producers ramp toward their new ceilings; a sixth consecutive monthly increase compounds on the five before it, adding several million barrels per day cumulatively to the pool the IEA tallies in its monthly supply-demand balance. IEA reporting through 2026 has already attributed a widening global surplus directly to successive OPEC+ output increases, so another approval in this run makes it more likely the next Oil Market Report shows the balance at or beyond a 1.0 mb/d surplus. Because the added barrels keep flowing once pumped rather than vanishing if a single meeting's decision is later reversed, the push behaves like a step that ramps in as production catches up to the new quota.",
        sources: [
          {
            url: "https://www.ecofinagency.com/news-industry/1610-49610-the-iea-forecasts-global-oil-surplus-in-2026-as-opec-increases-output",
            title:
              "The IEA Forecasts Global Oil Surplus in 2026 as OPEC+ Increases Output - Ecofin Agency",
            retrieved: "2026-09-21",
          },
          {
            url: "https://www.iea.org/commentaries/as-oil-market-surplus-keeps-rising-something-s-got-to-give",
            title: "As oil market surplus keeps rising, something’s got to give – Analysis - IEA",
            retrieved: "2026-09-21",
          },
        ],
        provenance: "documented",
        reflexive: false,
      },
    ],
    frontier: ["01M32K63YVGYPVQN443GE8T4JB"],
  },
  {
    event: "proposal_accepted",
    at: 10,
    proposition: null,
    links: [
      {
        id: "01M32K94B65XC2DW5NG6E0S5KG",
        source: "01M32K63YVGYPVQN443GE8T4JB",
        target: "01M32J8Q6FB1PPJ64XC5ECAPPS",
        mode: "trigger",
        strength: 0.35,
        lag: 5.0,
        shape: "ramp",
        half_life: null,
        rationale:
          "Futures markets price in OPEC+ quota decisions almost immediately rather than waiting for the monthly IEA balance report, so a sixth straight approved increase adds directly to the flat-price pressure on Brent as traders extrapolate a widening surplus from the production trend itself.",
        sources: [
          {
            url: "https://www.economies.com/commodities/oil-news/oil-under-the-microscope:-what-drove-prices-in-2025-and-what-lies-ahead-in-2026%20-48017",
            title:
              "Oil under the microscope: What drove prices in 2025 and what lies ahead in 2026?",
            retrieved: "2026-09-21",
          },
          {
            url: "https://finance.yahoo.com/news/oil-prices-expected-to-drop-below-60-on-increasing-opec-supply-172801653.html",
            title: "Oil prices expected to drop below $60 on increasing OPEC+ supply",
            retrieved: "2026-09-21",
          },
        ],
        provenance: "documented",
        reflexive: false,
      },
    ],
    frontier: ["01M32K63YVGYPVQN443GE8T4JB"],
  },
  {
    event: "proposal_accepted",
    at: 11,
    proposition: {
      id: "01M32KDG4TS3B3T9A1Q5X6FNFH",
      claim:
        "The U.S. Global Jets ETF (JETS) closes at least 8 percent above its price on the trading day immediately before Brent's five-session close under $68.00, at some point within the following 20 trading days.",
      kind: "market",
      resolution: {
        criteria:
          "JETS ETF's daily closing net asset value, as reported on NYSE Arca, reaches a level at least 8 percent above its closing price on the trading day immediately preceding the first of the five consecutive sessions in which Brent settles below $68.00, on any close within the following 20 trading sessions.",
        source: "NYSE Arca / U.S. Global Investors (JETS ETF daily closes)",
        by: "2027-03-31",
      },
      prior: {
        p: 0.5,
        lo: 0.32,
        hi: 0.68,
        owner: "model",
      },
      beliefs: {
        model: {
          p: 0.5,
          lo: 0.32,
          hi: 0.68,
          owner: "model",
        },
        user: null,
        market: null,
      },
      base_rate: null,
      evidence: [],
      payoff: {
        kind: "price",
        instrument: "U.S. Global Jets ETF (JETS)",
        direction: "long",
        move: 0.08,
      },
      not_tradeable_reason: null,
    },
    links: [
      {
        id: "01M32KDG4TS3B3T9A1Q5X6FNFJ",
        source: "01M32J8Q6FB1PPJ64XC5ECAPPS",
        target: "01M32KDG4TS3B3T9A1Q5X6FNFH",
        mode: "trigger",
        strength: 0.6,
        lag: 5.0,
        shape: "ramp",
        half_life: null,
        rationale:
          "Jet fuel is one of the largest single operating costs for passenger airlines and tracks crude prices closely, so a confirmed five-session settle under $68 gets read by the market as a durable drop in fuel input costs rather than a blip; analysts and investors then re-rate airline earnings forecasts upward over the following days, which lifts fuel-sensitive carrier shares that dominate JETS. Because the re-rating is a shift in expected forward margins rather than a day-to-day tracking of the oil price itself, the lift persists even if Brent later ticks back up somewhat, so the push is modeled as a one-time trigger that ramps in over about a week rather than a continuous hold.",
        sources: [
          {
            url: "https://www.investingdaily.com/146555/another-way-to-profit-from-a-drop-in-oil-prices/",
            title: "Taking a Flier on a Drop in Oil Prices - Investing Daily",
            retrieved: "2026-09-21",
          },
          {
            url: "https://www.kavout.com/market-lens/are-surging-oil-prices-grounding-airline-stocks",
            title: "Are Surging Oil Prices Grounding Airline Stocks",
            retrieved: "2026-09-21",
          },
        ],
        provenance: "documented",
        reflexive: false,
      },
    ],
    frontier: [],
  },
  {
    event: "verdict",
    kind: "reached",
    path: [
      "01M32HZYPTKVEGND75JWG353AC",
      "01M32JNTXX3D1ZMGWXDSP5B7ZC",
      "01M32J8Q6FB1PPJ64XC5ECAPPS",
    ],
    product: null,
    nearest: null,
    why: "The story reaches Brent crude oil settles below $68.00 per barrel for five consecutive trading sessions in 2 steps, along the best-backed route on this map.",
  },
  {
    event: "receipt",
    model: "claude-sonnet-5",
    calls: 15,
    input_tokens: 13108,
    output_tokens: 92949,
    cache_read_tokens: 1304498,
    searches: 55,
    dollars: 2.1714631000000004,
    seconds: 1644.6772355419816,
    mode: "live",
    recording_date: null,
    effort: "default",
    prompt_hash: "1c224cc32fb0e3f3b8b2508158affca16a3cc839d6a015d410e080ec276516ed",
  },
  {
    event: "done",
    reason: "reached_terminal",
    claims: 6,
    links: 9,
    rejected: 1,
  },
];
