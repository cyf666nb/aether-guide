# Frontend Visual Spec

## Direction

The MVP splits the system into two visual languages:

- **临境**: dark, photography-first tourist experience with a documentary feel.
- **札记**: light, editorial operations workbench with large serif data and fine lines.

The first three memory hooks are:

1. Full-bleed scenic image behind the digital human interaction surface.
2. 96px serif operational numbers in the admin dashboard.
3. Warm-gold scan and trace moments for AI, VPS, and loading states.

## Tokens

- Theme roots: `data-theme="linjing"` and `data-theme="zhaji"`.
- Atmosphere classes: `atmosphere-lake`, `atmosphere-dusk`, `atmosphere-ocean`, `atmosphere-desert`.
- Default atmosphere: forest, using `--accent-500: #4F6B4A`.
- Radius scale: 2 / 4 / 8 / 16px, with pill used only for chips and meters.
- Animation curves: `--ease-glide`, `--ease-paper`, and `--ease-spring`.

## Assets

Generated scene assets are project-local in both frontends:

- `public/scenes/forest.png`
- `public/scenes/lake.png`
- `public/scenes/dusk.png`
- `public/scenes/ocean.png`
- `public/scenes/desert.png`

The images are demo tenant assets and can later be replaced by real scenic photography without changing page logic.

## Pages

- Tourist `/`: digital human main interaction with trust bar, current spot, streaming text, citations, and voice field.
- Tourist `/photo`: black camera surface, SVG viewfinder, warm scan line, bottom result sheet.
- Tourist `/route`: time-first route timeline with generated scenic imagery.
- Admin `/`: data-news dashboard with asymmetrical 12-column layout.
- Admin `/knowledge`: document tree, version rail, preview and chunk hit treatment.
- Admin `/replay`: three synchronized timeline layers.
- Admin `/experiments`: prompt A/B editor mock and winner thermometer.
- Admin `/settings/atmosphere`: live accent switching.

