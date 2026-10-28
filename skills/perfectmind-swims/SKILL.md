---
name: perfectmind-swims
description: Find City of Markham drop-in lane swim times (Lane Swim and Endurance Lane Swim) for a date using the perfectmind MCP server. Use when the user asks about lane swimming, pool times, swim schedules, or drop-in swims in Markham or at Markham facilities such as Cornell, Pan Am Centre, Milliken Mills, Thornlea, Centennial, Angus Glen or Aaniin, e.g. "any lane swims tomorrow evening?", "when can I swim at Cornell on Friday?".
---

# Markham drop-in lane swims

The `perfectmind` MCP server reads the City of Markham PerfectMind booking site
(https://cityofmarkham.perfectmind.com). It is **read-only**: you can't book anything through it.

## Tool

`list_lane_swims(date, location?)`
- `date`: required, ISO `YYYY-MM-DD`. Convert relative phrases ("tonight", "tomorrow", "this Friday")
  to a concrete date first, using today's date in Toronto time (America/Toronto). For a range
  ("this weekend"), call once per day.
- `location`: optional, a case-insensitive substring of the facility name, such as `"Cornell"`, `"Pan Am"` or
  `"Milliken"`. If nothing at that location matches, the tool returns an error that lists the
  locations that do have lane swims that day. Use that list to pick the intended pool or tell the user.

Each session has: `name`, `start`/`end` (`HH:MM`, 24h local time), `location`, `address`, `facility` (pool and lanes),
`status`, `spots_left`, `price_range`, `age_restriction` and `booking_url`.

`status` meaning:
- `open`: registration is open, and `spots_left` shows the remaining spots
- `full`: no spots left (the site may offer a waitlist)
- `not_open`: registration is closed (the session started or passed) or not open yet. Residents can register
  for most drop-ins about **21 hours** before start time.

## How to answer

1. Resolve the date, and the location if the user gave one. Call the tool. Filter by time of day yourself
   (for example "evening" means start ≥ 17:00).
2. Present sessions sorted by start time. For a single location, use a compact list: `07:15–08:15 · 11 spots left`.
   For several locations, group by location and include the address once per location.
3. Mark Endurance Lane Swims (Pan Am Centre) separately from regular Lane Swims.
4. Show status clearly. For `not_open` sessions in the future, mention that booking opens about 21 h before start.
5. Link to `booking_url` for sessions the user is likely to book. Booking needs a City of Markham account
   on the website.
6. If the tool says the date is outside the published schedule, tell the user the valid range it reports.

## Scope and limits

- City of Markham only. Drop-in **lane** swims only. Recreational, Parent & Tot, Therapy swims, Aquafit and
  other programs are not supported yet.
- The data comes live from the public site. If a request fails, say so and suggest checking the website
  instead of guessing times.
