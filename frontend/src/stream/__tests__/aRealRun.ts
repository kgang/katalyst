/**
 * One real generation, kept whole: the ten-claim Hormuz map the coordinator's
 * first live run built on 2026-09-17.
 *
 * **Every number in here was measured, not written down.** It is the run's own
 * events, in the order they came off the wire, copied from the working file the
 * run left behind — the claims the model proposed and our rules accepted, the
 * identifiers the engine minted, the seed it drew with, and what the run cost.
 * Nothing in this file was chosen by anybody, and no test below reads a value out
 * of it and expects it to mean anything: the tests read its **shape** — ten
 * claims, nine arrows, four columns, twenty-six-character identifiers, claim
 * sentences of a hundred and seventy-six characters, and not one refusal.
 *
 * It is here because the chapter's worked run is three claims wide and one
 * column deep, and almost everything that goes wrong on a growing map goes wrong
 * on the fourth column: boxes landing on each other, the growing edge sliding off
 * the glass, an identifier reaching the screen. A fixture that cannot show those
 * is a fixture that cannot catch them.
 *
 * **It carries no world.** A recording never does: the likelihoods are worked out
 * again from the seed, which is what makes a replayed map and a live one agree by
 * construction.
 *
 * Source: `backend/.runs/hormuz-2026-09-17T15-20-12Z.json`, which that run wrote
 * and which nobody has edited. It became no recording, because it refused
 * nothing and every recording must show a refusal.
 */

import type { StreamEvent } from "../events";

/** The sentence the run was started from, exactly as it was typed. */
export const THE_REAL_SENTENCE = "The Strait of Hormuz is going to open next week.";

/**
 * The run, event by event. Thirteen of them: it starts, ten proposals are
 * accepted, the receipt arrives and it stops — at the width cap, because the
 * claim it was expanding already had every effect one generation draws from it.
 */
export const A_REAL_RUN = [
  {
    event: "generation_started",
    generation_id: "01M2QYMDG3QNFECTM3W1J5C0MM",
    seed: 4803646386380448000,
    seed_as_written: "4803646386380448080",
    hypothesis: "The Strait of Hormuz is going to open next week.",
    target: null,
  },
  {
    event: "proposal_accepted",
    at: 0,
    proposition: {
      id: "01M2QYMMJYA27CAZ91N8VPA6NK",
      claim: "The Strait of Hormuz reopens to normal commercial traffic next week.",
      kind: "hypothesis",
      resolution: {
        criteria: "Res ",
        source: "x ",
        by: "2026-09-30",
      },
      prior: {
        p: 0.3,
        lo: 0.1,
        hi: 0.5,
        owner: "model",
      },
      beliefs: {
        model: {
          p: 0.3,
          lo: 0.1,
          hi: 0.5,
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
    links: [],
    frontier: ["01M2QYMMJYA27CAZ91N8VPA6NK"],
  },
  {
    event: "proposal_accepted",
    at: 1,
    proposition: {
      id: "01M2QYS0PDR8KRE68K8YVR8MP0",
      claim:
        "With the strait open again, the war premium comes out of crude and Brent falls back toward pre-crisis levels within weeks.",
      kind: "market",
      resolution: {
        criteria:
          "ICE Brent front-month futures post official settlement prices at or below $80.00 per barrel on at least three consecutive trading sessions on or before 2026-10-31.",
        source:
          "ICE Futures Europe official daily settlement prices for Brent Crude (BRN) front-month contract",
        by: "2026-10-31",
      },
      prior: {
        p: 0.25,
        lo: 0.1,
        hi: 0.45,
        owner: "model",
      },
      beliefs: {
        model: {
          p: 0.25,
          lo: 0.1,
          hi: 0.45,
          owner: "model",
        },
        user: null,
        market: null,
      },
      base_rate: {
        reference_class:
          "Acute oil supply-disruption episodes since 1980 in which the blocked or lost barrels demonstrably resumed flowing (Iran-Iraq tanker war lulls 1984 and 1988, post-Desert Storm February 1991, Libya restart late 2011, Abqaiq repair September 2019, post-invasion price peak unwind mid-2022), counting how many saw front-month Brent/WTI fall at least 20% within 30 days of the resumption",
        k: 4,
        n: 6,
        sources: [],
      },
      evidence: [],
      payoff: {
        kind: "price",
        instrument: "ICE Brent Crude front-month futures (BRN)",
        direction: "short",
        move: 0.2,
      },
      not_tradeable_reason: null,
    },
    links: [
      {
        id: "01M2QYS0PDR8KRE68K8YVR8MP1",
        source: "01M2QYMMJYA27CAZ91N8VPA6NK",
        target: "01M2QYS0PDR8KRE68K8YVR8MP0",
        mode: "trigger",
        strength: 2.2,
        lag: 1.0,
        shape: "step",
        half_life: null,
        rationale:
          "Roughly a fifth of seaborne oil and most Gulf crude exports transit Hormuz, so the closure is the single fact holding the current war premium in the Brent curve; verified resumption of unrestricted commercial transit removes the supply constraint and lets war-risk insurance rates and freight fall, and paper crude reprices within a session or two rather than waiting for physical cargoes to land. The repricing is a one-time shove that persists even if tensions later flare again, which is why the push does not vanish with its cause. Banks have explicitly framed the downside case as Brent heading to the bottom of a $70-$100 range on even modest recovery of Hormuz flows, while the EIA's view that regional production lags until 2027 is the reason the fall may stop short of a full collapse.",
        sources: [
          {
            url: "https://www.cnbc.com/2026/08/24/oil-price-today-wti-brent-us-sanctions-iran.html",
            title: "Oil price today: WTI, Brent, U.S. sanctions, Iran",
            retrieved: "2026-09-17",
          },
          {
            url: "https://www.aljazeera.com/economy/2026/8/12/oil-prices-rise-as-attacks-dent-hopes-for-strait-of-hormuz-reopening",
            title:
              "Oil prices rise as attacks dent hopes for Strait of Hormuz reopening | Business and Economy News | Al Jazeera",
            retrieved: "2026-09-17",
          },
          {
            url: "https://www.cnbc.com/2026/06/26/oil-prices-middle-east-iran-strait-of-hormuz-opec-iraq-wti-brent-crude.html",
            title: "Oil prices fall as more tankers exit Strait of Hormuz",
            retrieved: "2026-09-17",
          },
        ],
        provenance: "documented",
        reflexive: false,
      },
    ],
    frontier: ["01M2QYMMJYA27CAZ91N8VPA6NK"],
  },
  {
    event: "proposal_accepted",
    at: 2,
    proposition: {
      id: "01M2QYTGND4WFW3MQFND2TCFZM",
      claim:
        "Once the trapped tanker fleet is released and Gulf loadings resume, VLCC spot earnings on the Middle East Gulf\u2013China route collapse from crisis peaks back toward normal levels.",
      kind: "market",
      resolution: {
        criteria:
          "The Baltic Exchange TD3C (Ras Tanura\u2013Ningbo, 270,000 mt) time-charter-equivalent assessment prints below USD 100,000/day on at least five consecutive publication days.",
        source: "Baltic Exchange daily tanker market report (TD3C TCE assessment)",
        by: "2026-11-15",
      },
      prior: {
        p: 0.35,
        lo: 0.15,
        hi: 0.6,
        owner: "model",
      },
      beliefs: {
        model: {
          p: 0.35,
          lo: 0.15,
          hi: 0.6,
          owner: "model",
        },
        user: null,
        market: null,
      },
      base_rate: {
        reference_class:
          "Episodes since 2000 in which the VLCC Middle East Gulf\u2013Far East spot TCE benchmark exceeded USD 200,000/day and then fell back below USD 100,000/day within 60 days of the peak (2004 Q4, 2008 Q2, Oct 2019 COSCO sanctions, Mar\u2013Apr 2020 floating-storage spike, Dec 2022, Feb 2024)",
        k: 5,
        n: 6,
        sources: [],
      },
      evidence: [],
      payoff: {
        kind: "price",
        instrument: "Frontline plc (NYSE: FRO) common shares",
        direction: "short",
        move: 0.25,
      },
      not_tradeable_reason: null,
    },
    links: [
      {
        id: "01M2QYTGND4WFW3MQFND2TCFZN",
        source: "01M2QYMMJYA27CAZ91N8VPA6NK",
        target: "01M2QYTGND4WFW3MQFND2TCFZM",
        mode: "sustain",
        strength: 2.2,
        lag: 21.0,
        shape: "ramp",
        half_life: null,
        rationale:
          "The crisis freight spike is a tonnage-availability shock: roughly 77 VLCCs (about 9% of the fleet) were reported trapped east of Hormuz and charterers bid MEG\u2013China voyages to record levels, with TD3C reportedly assessed above USD 400,000/day. Reopening restores transit, releases the trapped ships back into the spot pool and removes the diversion and waiting time that inflated tonne-mile demand, so earnings mean-revert over a few weeks of fixture cycles. The push only holds while transit continues \u2014 a re-closure would immediately re-tighten supply and re-spike rates.",
        sources: [
          {
            url: "https://www.useluminix.com/reports/industry-analysis/economic-impact-analysis-strait-of-hormuz-closure-through-april-2026/source/4",
            title:
              "Research maritime war-risk insurance rate history for the Strait of Hormuz and Persian Gulf region, including the rate spikes\u2026",
            retrieved: "2026-09-17",
          },
          {
            url: "https://www.howdenre.com/sites/howdenre.howdenprod.com/files/2026-03/HowdenRe_Strait_of_Hormuz_report_March272026.pdf",
            title: "Howden Re Compiled by Business Intelligence 26th March 2026 Strait of Hormuz:",
            retrieved: "2026-09-17",
          },
        ],
        provenance: "documented",
        reflexive: false,
      },
    ],
    frontier: ["01M2QYMMJYA27CAZ91N8VPA6NK"],
  },
  {
    event: "proposal_accepted",
    at: 3,
    proposition: {
      id: "01M2QYVW9CJRCYRNQYJS7Y1W8V",
      claim:
        "With the strait open, Qatar's LNG loadings restart and monthly seaborne LNG exports through Hormuz climb back to most of their pre-crisis level.",
      kind: "event",
      resolution: {
        criteria:
          "Total laden LNG exports loaded in Qatar and transiting the Strait of Hormuz reach at least 6.0 million tonnes in a single calendar month (roughly 70% or more of the pre-crisis monthly average of about 8.5 Mt) in any calendar month up to and including November 2026.",
        source: "Kpler vessel-tracking data on Qatari LNG loadings as reported by Reuters",
        by: "2026-12-10",
      },
      prior: {
        p: 0.42,
        lo: 0.18,
        hi: 0.68,
        owner: "model",
      },
      beliefs: {
        model: {
          p: 0.42,
          lo: 0.18,
          hi: 0.68,
          owner: "model",
        },
        user: null,
        market: null,
      },
      base_rate: {
        reference_class:
          "Large LNG export terminals idled by armed conflict or major physical incident since 2000 (e.g. Ras Laffan 2005 explosion, Egypt 2013, Yemen LNG 2015, Freeport 2022, Gorgon/Wheatstone outages) that returned to at least 70% of pre-outage monthly export volumes within ten weeks of the physical constraint being removed",
        k: 5,
        n: 9,
        sources: [],
      },
      evidence: [],
      payoff: null,
      not_tradeable_reason: null,
    },
    links: [
      {
        id: "01M2QYVW9CJRCYRNQYJS7Y1W8W",
        source: "01M2QYMMJYA27CAZ91N8VPA6NK",
        target: "01M2QYVW9CJRCYRNQYJS7Y1W8V",
        mode: "sustain",
        strength: 2.6,
        lag: 14.0,
        shape: "ramp",
        half_life: null,
        rationale:
          "Around 93% of Qatar's LNG exports and about a fifth of all global LNG trade physically transit the Strait of Hormuz, and the IEA notes there is no alternative route for those volumes, so Qatari loadings can only resume while the strait is passable \u2014 the push holds only as long as it stays open. Restart is not instant: carriers must be repositioned, war-risk cover rewritten and liquefaction trains ramped, which is why the effect builds over roughly two weeks rather than landing the same day. Any war damage to Ras Laffan caps how much of the volume comes back, which is why the arrow is strong but not decisive.",
        sources: [
          {
            url: "https://www.iea.org/topics/the-middle-east-and-global-energy-markets",
            title: "The Middle East and Global Energy Markets \u2013 Topics - IEA",
            retrieved: "2026-09-17",
          },
          {
            url: "https://www.iea.org/about/oil-security-and-emergency-response/strait-of-hormuz",
            title: "Strait of Hormuz - About - IEA",
            retrieved: "2026-09-17",
          },
          {
            url: "https://www.congress.gov/crs-product/R45281",
            title:
              "The Strait of Hormuz: Security Developments and Impacts on Oil, Gas, and Other Commodities | Congress.gov | Library of Congress",
            retrieved: "2026-09-17",
          },
        ],
        provenance: "documented",
        reflexive: false,
      },
    ],
    frontier: ["01M2QYVW9CJRCYRNQYJS7Y1W8V"],
  },
  {
    event: "proposal_accepted",
    at: 4,
    proposition: {
      id: "01M2QYWZZHXV6FRRRCAZAA21BG",
      claim:
        "Once Qatari cargoes are flowing through Hormuz again, the European gas price spike unwinds and front-month TTF falls sharply from its crisis level.",
      kind: "market",
      resolution: {
        criteria:
          "The ICE Endex Dutch TTF front-month natural gas futures contract records at least one daily settlement price that is 25% or more below its official settlement price of 2026-09-16, on any trading day from 2026-09-17 through 2026-12-31 inclusive. Settlement prices as published in ICE Endex daily settlement reports; the front-month contract is whichever monthly contract is nearest to expiry on each date.",
        source:
          "ICE Endex official daily settlement prices for Dutch TTF Natural Gas Futures (TFM)",
        by: "2026-12-31",
      },
      prior: {
        p: 0.76,
        lo: 0.55,
        hi: 0.9,
        owner: "model",
      },
      beliefs: {
        model: {
          p: 0.76,
          lo: 0.55,
          hi: 0.9,
          owner: "model",
        },
        user: null,
        market: null,
      },
      base_rate: {
        reference_class:
          "Episodes since 2010 in which ICE TTF front-month gas rose 50% or more within a quarter on a supply-side disruption, and the disrupted supply subsequently returned; counted as true if front-month settled 25% or more below the pre-restoration peak-period level within 90 days of supply returning.",
        k: 7,
        n: 9,
        sources: [],
      },
      evidence: [],
      payoff: {
        kind: "price",
        instrument: "ICE Endex Dutch TTF Natural Gas Futures (TFM) front-month",
        direction: "short",
        move: 0.3,
      },
      not_tradeable_reason: null,
    },
    links: [
      {
        id: "01M2QYWZZHXV6FRRRCAZAA21BH",
        source: "01M2QYVW9CJRCYRNQYJS7Y1W8V",
        target: "01M2QYWZZHXV6FRRRCAZAA21BG",
        mode: "sustain",
        strength: 1.7,
        lag: 10.0,
        shape: "ramp",
        half_life: null,
        rationale:
          "Qatar's Ras Laffan exports are roughly a fifth of global LNG supply, and their loss through Hormuz is the single largest physical cause of the current TTF spike; restored loadings put those cargoes back into the Atlantic and Asian balances, which removes the scarcity premium that Europe is paying to outbid Asia for Atlantic-basin volumes. The push is continuous rather than one-off: it exists only while Qatari cargoes actually sail, and a renewed halt would send the premium straight back. The lag and ramp reflect the three-to-four week voyage and cargo-scheduling cycle before restored loadings show up as delivered supply.",
        sources: [
          {
            url: "https://www.kpler.com/blog/global-lng-and-natural-gas-prices-surge-as-us-and-iran-resume-hot-war",
            title:
              "Hormuz Crisis Drives TTF to Highest Level Since 2023 Global LNG and natural gas prices surge as US and Iran resume hot war | Kpler - Jul 24, 2026",
            retrieved: "2026-09-17",
          },
          {
            url: "https://www.eia.gov/todayinenergy/detail.php?id=67604",
            title:
              "International LNG prices rise amid Strait of Hormuz closure - U.S. Energy Information Administration (EIA)",
            retrieved: "2026-09-17",
          },
          {
            url: "https://www.cnbc.com/2026/03/03/middle-east-war-gas-energy-lng-drone-qatar-strait-hormuz-price-shock.html",
            title: "Natural gas, LNG prices soar on Middle East supply fears",
            retrieved: "2026-09-17",
          },
          {
            url: "https://www.energyaspects.com/resources/insights/qatar-lng-hormuz-recovery-gradual",
            title: "Qatar LNG: why Hormuz recovery will be slow and uneven",
            retrieved: "2026-09-17",
          },
        ],
        provenance: "documented",
        reflexive: false,
      },
    ],
    frontier: ["01M2QYVW9CJRCYRNQYJS7Y1W8V"],
  },
  {
    event: "proposal_accepted",
    at: 5,
    proposition: {
      id: "01M2QYY7TQZ5NVS0QS3AQSZ8EQ",
      claim:
        "With Qatari cargoes loading again, the Asian spot LNG spike deflates and front-month JKM futures settle far below their crisis peak.",
      kind: "market",
      resolution: {
        criteria:
          "Front-month CME Japan Korea Marker (Platts) LNG futures (code JKM) settle at or below 70% of their highest front-month settlement recorded during the crisis window (the maximum front-month settlement between 2026-08-01 and the day the Strait of Hormuz reopens), on at least three consecutive trading days, on or before 2026-11-30.",
        source:
          "CME Group daily settlement data for the Japan Korea Marker (Platts) LNG futures contract",
        by: "2026-11-30",
      },
      prior: {
        p: 0.72,
        lo: 0.48,
        hi: 0.88,
        owner: "model",
      },
      beliefs: {
        model: {
          p: 0.72,
          lo: 0.48,
          hi: 0.88,
          owner: "model",
        },
        user: null,
        market: null,
      },
      base_rate: {
        reference_class:
          "Episodes since 2010 in which front-month JKM rose at least 50% above its prior three-month average on a supply disruption (Fukushima-era tightness, 2021 winter squeeze, 2022 Freeport outage, 2022 European restocking, 2023 Australian strike threat, 2024-25 Red Sea rerouting) and the disruption was subsequently resolved or eased; counted as true if front-month JKM fell at least 30% from its peak within ten weeks of the easing.",
        k: 4,
        n: 6,
        sources: [],
      },
      evidence: [],
      payoff: {
        kind: "price",
        instrument: "CME Japan Korea Marker (Platts) LNG front-month futures (JKM)",
        direction: "short",
        move: 0.35,
      },
      not_tradeable_reason: null,
    },
    links: [
      {
        id: "01M2QYY7TQZ5NVS0QS3AQSZ8ER",
        source: "01M2QYVW9CJRCYRNQYJS7Y1W8V",
        target: "01M2QYY7TQZ5NVS0QS3AQSZ8EQ",
        mode: "trigger",
        strength: 1.5,
        lag: 14.0,
        shape: "ramp",
        half_life: null,
        rationale:
          "Qatar is the single largest supplier of LNG into Asia and essentially all of it sails through Hormuz, so its loadings halting removes roughly a fifth of global supply and its loadings restarting puts that volume back. Asian spot buyers bid JKM up during the outage to outcompete Europe for non-Qatari cargoes; once Qatari vessels are loading and the arrival schedule refills over the two-to-three week voyage, that scarcity bid disappears and the paper curve reprices ahead of physical delivery. The price drop, once recorded in settlements, is locked in even if the strait were later disrupted again, which is why this is a one-time shove rather than a continuous hold.",
        sources: [],
        provenance: "argued",
        reflexive: false,
      },
    ],
    frontier: ["01M2QYVW9CJRCYRNQYJS7Y1W8V"],
  },
  {
    event: "proposal_accepted",
    at: 6,
    proposition: {
      id: "01M2QZ0440X3SBT5DX0G5DRN2K",
      claim:
        "With Qatari cargoes sailing again and prices collapsing, Europe manages a late scramble to refill and ends the injection season with storage at least 80% full.",
      kind: "event",
      resolution: {
        criteria:
          "GIE AGSI+ reports EU aggregate gas storage fullness of at least 80.0% for gas day 2026-11-01 (as published in the AGSI+ historical dataset, first published value for that gas day or later revision available on 2026-11-05).",
        source:
          "Gas Infrastructure Europe AGSI+ (agsi.gie.eu) EU aggregate storage fullness series",
        by: "2026-11-05",
      },
      prior: {
        p: 0.3,
        lo: 0.12,
        hi: 0.52,
        owner: "model",
      },
      beliefs: {
        model: {
          p: 0.3,
          lo: 0.12,
          hi: 0.52,
          owner: "model",
        },
        user: null,
        market: null,
      },
      base_rate: {
        reference_class:
          "Years 2011-2025 in which EU-wide aggregate gas storage fullness stood at or above 80% on 1 November, per GIE AGSI+ EU aggregate series",
        k: 12,
        n: 15,
        sources: [],
      },
      evidence: [],
      payoff: null,
      not_tradeable_reason: null,
    },
    links: [
      {
        id: "01M2QZ0440X3SBT5DX0G5DRN2M",
        source: "01M2QYVW9CJRCYRNQYJS7Y1W8V",
        target: "01M2QZ0440X3SBT5DX0G5DRN2K",
        mode: "trigger",
        strength: 0.9,
        lag: 20.0,
        shape: "step",
        half_life: null,
        rationale:
          "Hormuz carried roughly a fifth of global LNG trade before the war, with Qatar the dominant shipper, and its loss removed hundreds of millions of cubic metres a day of supply through the whole 2026 injection season; restored Qatari loadings both add physical cargoes Europe can bid for and break the price level that made marginal injections uneconomic. Ras Laffan to northwest Europe via Suez is roughly eighteen to twenty days, so the first restored cargoes land inside the final weeks of injection season. Because gas injected into storage stays injected, the push on the 1 November stock level survives any later re-disruption.",
        sources: [
          {
            url: "https://www.iea.org/topics/the-middle-east-and-global-energy-markets",
            title: "The Middle East and Global Energy Markets \u2013 Topics - IEA",
            retrieved: "2026-09-17",
          },
          {
            url: "https://www.euronews.com/business/2026/08/31/qatarenergy-extends-lng-cancellations-into-november-as-hormuz-disruption-drags-on",
            title: "Qatar extends LNG cancellations as Hormuz disruption drags on",
            retrieved: "2026-09-17",
          },
        ],
        provenance: "documented",
        reflexive: false,
      },
    ],
    frontier: ["01M2QZ0440X3SBT5DX0G5DRN2K"],
  },
  {
    event: "proposal_accepted",
    at: 7,
    proposition: {
      id: "01M2QZ20C1F08CDA36TBC0FJ5G",
      claim:
        "With storage confirmed at least 80% full going into winter, the rationing premium drains out of the Q1-2027 TTF contract and it trades back down to pre-crisis territory.",
      kind: "market",
      resolution: {
        criteria:
          "The ICE Endex Dutch TTF natural gas quarterly futures contract for Q1 2027 (Jan-Mar 2027 delivery) records an official daily settlement price at or below EUR 40.00/MWh on at least one trading day on or before 2026-12-31.",
        source:
          "ICE Endex daily settlement prices (TTF Hi Cal Month/Quarter futures, contract TFM/TFQ) as published by Intercontinental Exchange",
        by: "2026-12-31",
      },
      prior: {
        p: 0.28,
        lo: 0.12,
        hi: 0.5,
        owner: "model",
      },
      beliefs: {
        model: {
          p: 0.28,
          lo: 0.12,
          hi: 0.5,
          owner: "model",
        },
        user: null,
        market: null,
      },
      base_rate: {
        reference_class:
          "European supply-shock gas price spikes since 2009 in which front-winter TTF/NBP more than doubled from its pre-shock level and the disrupted supply was subsequently physically restored, counting how many saw the front-winter contract settle back within 25% of the pre-shock level within 120 days of restoration",
        k: 4,
        n: 7,
        sources: [],
      },
      evidence: [],
      payoff: {
        kind: "price",
        instrument: "ICE Endex TTF natural gas futures, Q1-2027 delivery (TFQ Q1 2027)",
        direction: "short",
        move: 0.45,
      },
      not_tradeable_reason: null,
    },
    links: [
      {
        id: "01M2QZ20C1F08CDA36TBC0FJ5H",
        source: "01M2QZ0440X3SBT5DX0G5DRN2K",
        target: "01M2QZ20C1F08CDA36TBC0FJ5G",
        mode: "trigger",
        strength: 1.4,
        lag: 5.0,
        shape: "step",
        half_life: null,
        rationale:
          "End-of-injection storage fullness is the single most-watched input into European winter gas pricing: the Q1 contract carries an explicit rationing premium that exists only while a low-stock winter looks possible. Bank scenario work during this crisis tied triple-digit December-2026 TTF to a storage shortfall carrying into winter, so a confirmed 80%-plus end-October level removes the scenario the premium is paid for. Once the season closes at that level the fact is fixed and cannot be undone by later news, so the repricing persists even if headlines turn again.",
        sources: [
          {
            url: "https://www.investing.com/news/commodities-news/european-gas-prices-could-jump-130-on-hormuz-disruption-goldman-estimates-4534261",
            title: "European gas prices extend gains to 50% on QatarEnergy halt By Investing.com",
            retrieved: "2026-09-17",
          },
          {
            url: "https://www.energyaspects.com/resources/insights/europe-gas-storage-ttf-outlook-summer-2026",
            title: "Europe gas storage shortfall and TTF price outlook",
            retrieved: "2026-09-17",
          },
        ],
        provenance: "documented",
        reflexive: false,
      },
    ],
    frontier: ["01M2QZ0440X3SBT5DX0G5DRN2K"],
  },
  {
    event: "proposal_accepted",
    at: 8,
    proposition: {
      id: "01M2QZ46T8RPDH1M7GV8WW0TDA",
      claim:
        "With storage confirmed comfortably full, the winter scarcity premium leaves German power and the Q1-2027 baseload future trades back down near its pre-crisis level.",
      kind: "market",
      resolution: {
        criteria:
          "The EEX German Power Base Q1-2027 future (Phelix-DE quarterly baseload) posts a daily settlement price at or below EUR 140.00/MWh on at least one trading day between 2026-11-01 and 2026-12-31 inclusive.",
        source: "EEX published daily settlement prices for German Power Base Quarter Futures",
        by: "2026-12-31",
      },
      prior: {
        p: 0.55,
        lo: 0.3,
        hi: 0.78,
        owner: "model",
      },
      beliefs: {
        model: {
          p: 0.55,
          lo: 0.3,
          hi: 0.78,
          owner: "model",
        },
        user: null,
        market: null,
      },
      base_rate: {
        reference_class:
          "Deliveries Q1-2012 through Q1-2026 (15 cases): the EEX German Power Base Q1 future's settlement at any point during November-December of the preceding year at or below EUR 140/MWh. Only the 2021-22 and 2022-23 crisis winters fail the test.",
        k: 13,
        n: 15,
        sources: [],
      },
      evidence: [],
      payoff: {
        kind: "price",
        instrument: "EEX German Power Base Q1-2027 Future (Phelix-DE quarterly baseload)",
        direction: "short",
        move: 0.25,
      },
      not_tradeable_reason: null,
    },
    links: [
      {
        id: "01M2QZ46T8RPDH1M7GV8WW0TDB",
        source: "01M2QZ0440X3SBT5DX0G5DRN2K",
        target: "01M2QZ46T8RPDH1M7GV8WW0TDA",
        mode: "trigger",
        strength: 1.1,
        lag: 7.0,
        shape: "ramp",
        half_life: null,
        rationale:
          "Gas-fired plant sets the marginal price in German winter hours, so power forwards for Q1 carry whatever scarcity premium the gas curve carries; an official storage figure at or above 80% going into winter removes the tail where gas must be rationed and forces power forwards to reprice off a normalised gas curve rather than a scarcity one. The repricing is a one-way ratchet in the sense that once traders have marked the premium out, a later fall in storage does not restore the same premium automatically, and it takes days to a fortnight as storage data and weather forecasts are digested. Pre-crisis reference point: the German Cal-2027 baseload future was trading around EUR 104/MWh in late July 2026, so a Q1-2027 print at or below EUR 140/MWh is a return to roughly normal winter shaping.",
        sources: [
          {
            url: "https://www.tacto.ai/en/energy/electricity-price",
            title: "Electricity Price Today: Price, Trends & Forecast 2026 | Tacto",
            retrieved: "2026-09-17",
          },
        ],
        provenance: "documented",
        reflexive: false,
      },
    ],
    frontier: ["01M2QZ0440X3SBT5DX0G5DRN2K"],
  },
  {
    event: "proposal_accepted",
    at: 9,
    proposition: {
      id: "01M2QZ8D1D98KVM20B6FG6F0V4",
      claim:
        "With European storage confirmed comfortably full, the winter scarcity premium in the curve collapses and TTF stops pricing next winter far above the following summer.",
      kind: "market",
      resolution: {
        criteria:
          "On at least one settlement date on or before 2026-12-31, the ICE Endex TTF Q1-2027 quarterly futures settlement price minus the ICE Endex TTF Summer-2027 (April-September 2027) seasonal futures settlement price is less than or equal to EUR 2.00 per MWh (including any negative value, i.e. Summer-2027 at a premium).",
        source:
          "ICE Endex official daily settlement prices for TTF Hi Cal Month/Quarter/Season futures (ICE Report Center)",
        by: "2027-01-05",
      },
      prior: {
        p: 0.55,
        lo: 0.3,
        hi: 0.75,
        owner: "model",
      },
      beliefs: {
        model: {
          p: 0.55,
          lo: 0.3,
          hi: 0.75,
          owner: "model",
        },
        user: null,
        market: null,
      },
      base_rate: null,
      evidence: [],
      payoff: {
        kind: "price",
        instrument:
          "ICE Endex TTF calendar spread: short Q1-2027 quarterly future, long Summer-2027 (Apr-Sep 2027) seasonal future, equal volumes",
        direction: "long",
        move: 0.15,
      },
      not_tradeable_reason: null,
    },
    links: [
      {
        id: "01M2QZ8D1ERH6TY33B9P950X67",
        source: "01M2QZ0440X3SBT5DX0G5DRN2K",
        target: "01M2QZ8D1D98KVM20B6FG6F0V4",
        mode: "trigger",
        strength: 1.4,
        lag: 21.0,
        shape: "ramp",
        half_life: null,
        rationale:
          "The premium of prompt winter over the following summer is the market's price for the risk of running out of gas mid-winter; it is a scarcity option, not a transport or storage cost. Once the injection season ends with inventories at or above 80% and Qatari cargoes are again loading, that option loses most of its value and the curve reverts toward its normal carry relationship, where summer trades at or near a premium to the winter behind it. The repricing is a one-off re-rating of the curve shape that persists after the storage figure itself is old news, and it builds over a few weeks as end-of-season data and revised EU filling-trajectory guidance are published.",
        sources: [
          {
            url: "https://www.oxfordenergy.org/publications/eu-gas-storage-regulation-a-journey-from-crisis-induced-rigidity-to-increased-flexibility/",
            title:
              "EU Gas Storage Regulation: a journey from crisis-induced rigidity to increased flexibility - Oxford Institute for Energy Studies",
            retrieved: "2026-09-17",
          },
          {
            url: "https://www.acer.europa.eu/news/eu-will-need-higher-lng-imports-refill-gas-storage-ahead-winter",
            title:
              "The EU will need higher LNG imports to refill gas storage ahead of winter | www.acer.europa.eu",
            retrieved: "2026-09-17",
          },
        ],
        provenance: "documented",
        reflexive: false,
      },
    ],
    frontier: [],
  },
  {
    event: "receipt",
    model: "claude-opus-5",
    calls: 10,
    input_tokens: 7931,
    output_tokens: 28753,
    cache_read_tokens: 325576,
    searches: 9,
    dollars: 1.32289925,
    seconds: 654.8896765419922,
    mode: "live",
    recording_date: null,
    prompt_hash: "93f859807d34b009f86c96f5ab59376ae122a665cf231a20de02a6560f68b087",
  },
  {
    event: "done",
    reason: "width_cap",
    claims: 10,
    links: 9,
    rejected: 0,
  },
] as readonly StreamEvent[];
