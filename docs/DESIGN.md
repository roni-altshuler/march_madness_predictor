# March Lab design

The primary inspiration is the official NCAA bracket experience: tournament
year, region and round navigation precede matchup drilldown. Branding, markup,
styles and graphics are original; no NCAA/team logos or proprietary assets are
copied. Useful sibling-project conventions survive: visible probability text,
monospaced statistics, explicit missing data and a dedicated evidence surface.

Dark navy surfaces, high-contrast neutral typography, blue prediction/link
accents, green winner marks and an amber unknown-field label form one coherent
identity. Spacing uses an 8px rhythm with restrained rounded borders. Fonts are
local system UI and Consolas/monospace: no external font requests or web assets.

The bracket positions cards at arithmetic centers of their feeding blocks.
SVG connectors share those coordinates. Four regions expose manageable 16-team
trees; Final Four navigation exposes the final two rounds. Desktop/tablet
brackets scroll within their own frame. On mobile, a round selector exposes
one readable matchup list at a time, while the page stays within the
viewport. Year/region controls and all game cards are buttons or labeled native
controls. Dialogs use the native modal element with Escape, focus trapping and
focus restoration. A skip link, current-page navigation state, explicit input
labels, status/error announcements and reduced-motion support are included.

Actual winners and probabilities are labeled separately. Scores appear only
when independently matched. Simulated draws have a distinct view label and
represent one path; the advancement table integrates all paths. Unknown 2027
entrants appear as an intentional empty state with the calendar and valid
import workflow. Import/validation failures are visible and do not alter files.

1440px desktop, 768px tablet and 390px mobile layouts are checked; screenshots are captured by real browser tests and
visually inspected. The UI is static ES modules served with a local Python API;
no frontend dependency bundle, login or network service is required.
