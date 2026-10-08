**Scope note:** The image is a narrow mobile capture (about 240px wide) and cuts off around the "Compétence sélectionnée" card. I can't judge the full graph size, the skill section, or the desktop layout. I made no edits. Mobile navigation and skill buttons are excluded, as you asked.

**What works, briefly:** The copy is honest. "Résultats simulés · taxonomie provisoire · transfert musical non validé" and the "Ces liens n'indiquent aucun prérequis pédagogique" note are the right instincts for a jury. The two-tone headline is a decent start.

**Six highest-impact changes**

1. **Make the graph the hero, not an icon in a card.** At this size the constellation is a decorative thumbnail. Its labels are about 5px and unreadable, and the nodes are just numbered circles. Move it above the fold, drop the card chrome, and go full-bleed on mobile. Keep labels at 12px or larger, or show labels only for the selected node and put the rest in a detail panel. The graph should be the thing the jury remembers.

2. **Fix the truncated controls.** "Atelier mu" and "Profil simu" are clipped in the selects, and the two labels don't align: "ESPACE D'EXPLORATION" wraps to two lines while "APPRENANT" doesn't. These are the primary controls, so replace them with a segmented control or a bottom sheet that shows full labels.

3. **Make the simulation disclaimer a structural element, not a footnote.** The most important fact for this project, that every value is simulated, is currently the smallest, dimmest text on the screen. Give it a persistent frame: a "MODÈLE SIMULÉ · DONNÉES FICTIVES" stamp on the graph itself, with the "non validé" line at a readable size. Treat honesty as the signature visual, not as small print.

4. **Remove the overclaim "GRU causal."** A green "causal" badge on a simulated model tells the jury the model makes causal claims, which is the opposite of what you're saying. Replace it with plain language such as "DKT (GRU) · simulé · corrélationnel," and drop the green badge styling.

5. **Commit to a distinct art direction built on the concept "déclic."** Right now it's a dark-navy SaaS dashboard: stacked rounded cards, teal and coral pills, chevron selects. Some options:
   - Use "déclic" (a click, a moment of insight) as the visual idea. A single moment of illumination on the graph would be stronger than a generic node cloud.
   - Use a characterful display face for the headline and a mono face for data. Current type is one neutral grotesk throughout, with no typographic personality.
   - Use a music-derived grid, such as staff lines or rhythm marks, instead of card borders.
   - Flatten the card-in-card nesting into one surface with hairline dividers.
   - Cut the green/coral dashboard palette to one warm accent for "fragile" and one neutral for everything else.

6. **Make the weakness answer and the interactions legible.**
   - The "next weakness" is currently encoded only as a coral dot in a two-item legend. That's color-only and doesn't say what the weakness is. Add one plain sentence above the graph, such as "Prochaine fragilité : [compétence], parce que [raison simulée]," so the jury gets the answer without decoding dots.
   - Nodes give no affordance that they're tappable. Add a visible "Touchez un nœud" hint and a selected state.
   - "Détail du modèle ↗" is a tiny text link. Make it a real button.

**Contrast and readability:** The eyebrow labels ("OBSERVER. ANTICIPER. PRATIQUER.", "LEARNING DIGITAL TWIN") and the grey body copy are small, letterspaced, and low contrast on near-black. Raise the minimum size and check the grey against WCAG AA.

I didn't create a plan file because this was a read-only critique. If you want, I can turn items 1, 2, and 5 into a concrete implementation plan.
