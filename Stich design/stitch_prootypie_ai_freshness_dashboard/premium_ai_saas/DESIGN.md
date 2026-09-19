---
name: Premium AI SaaS
colors:
  surface: '#fff7fa'
  surface-dim: '#e0d8dc'
  surface-bright: '#fff7fa'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#faf1f5'
  surface-container: '#f4ecf0'
  surface-container-high: '#eee6ea'
  surface-container-highest: '#e9e0e4'
  on-surface: '#1e1a1e'
  on-surface-variant: '#4d444c'
  inverse-surface: '#332f32'
  inverse-on-surface: '#f7eef3'
  outline: '#7e747d'
  outline-variant: '#d0c3cc'
  surface-tint: '#77517b'
  primary: '#38173e'
  on-primary: '#ffffff'
  primary-container: '#502d55'
  on-primary-container: '#c296c5'
  inverse-primary: '#e6b7e8'
  secondary: '#8a496b'
  on-secondary: '#ffffff'
  secondary-container: '#fdacd3'
  on-secondary-container: '#7a3b5d'
  tertiary: '#302210'
  on-tertiary: '#ffffff'
  tertiary-container: '#483724'
  on-tertiary-container: '#b8a087'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffd6ff'
  primary-fixed-dim: '#e6b7e8'
  on-primary-fixed: '#2e0d34'
  on-primary-fixed-variant: '#5e3a62'
  secondary-fixed: '#ffd8e8'
  secondary-fixed-dim: '#ffafd5'
  on-secondary-fixed: '#3a0526'
  on-secondary-fixed-variant: '#6f3253'
  tertiary-fixed: '#f9dec3'
  tertiary-fixed-dim: '#dcc2a8'
  on-tertiary-fixed: '#261908'
  on-tertiary-fixed-variant: '#554430'
  background: '#fff7fa'
  on-background: '#1e1a1e'
  surface-variant: '#e9e0e4'
typography:
  display-lg:
    fontFamily: Manrope
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-md:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Manrope
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Manrope
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Manrope
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.05em
  caption:
    fontFamily: Manrope
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  container-max: 1440px
  gutter: 24px
  margin-desktop: 64px
  margin-mobile: 20px
  glass-padding: 32px
---

## Brand & Style

This design system is anchored in a philosophy of "Quiet Intelligence." It targets a sophisticated audience that values both high-performance AI and an editorial, calming aesthetic. The UI avoids the typical neon-heavy "cyberpunk" tropes of AI, opting instead for a luxurious, macOS-inspired environment that feels stable, expensive, and intentional.

The style is a refined blend of **Modern Minimalism** and **Glassmorphism**. It utilizes translucency to create a sense of physical space—as if the interface is composed of layers of polished glass resting on a warm, organic surface. Every interaction is designed to feel effortless, using generous whitespace to reduce cognitive load and focus the user’s attention on AI-driven insights.

## Colors

The palette creates a warm, high-contrast experience that feels premium and inviting. 

- **Primary (Deep Violet):** Used for core branding, primary action buttons, and high-level structural headings. It provides the "weight" in the design.
- **Secondary (Muted Plum):** Used for interactive sub-elements, accents in data visualization, and hover states.
- **Accent (Creamy Sand):** Acts as a soft highlight color for backgrounds of secondary modules or subtle dividers.
- **Background (Off-white/Beige):** The "canvas" of the application. It is a warm, paper-like neutral that prevents the eye fatigue often caused by pure white.

For glass elements, use a semi-transparent white base with a high backdrop-blur (20px+) to ensure legibility of text over shifting background content.

## Typography

The design system utilizes **Manrope** for its technical precision and modern balance. It is a font that feels both human and engineered, fitting the AI SaaS narrative perfectly.

- **Scale:** High contrast between display titles and body text to create a clear hierarchy.
- **Tracking:** Headings use slight negative tracking for a tighter, more "editorial" feel. Labels use increased tracking and uppercase styling to differentiate functional metadata from narrative content.
- **Color:** Use the Primary Deep Violet for headings to anchor the page, and a 70% opacity variant for secondary body text to maintain a soft visual hierarchy.

## Layout & Spacing

The layout philosophy is a **Fixed-Fluid Hybrid**. On desktop, content is contained within a 1440px max-width container to maintain readability, while the background color extends to the screen edges.

- **Grid:** A 12-column grid is used for core content. Components like the sidebar (inspired by the sketch) should occupy 2-3 columns, while the main "Analysis" area spans the remainder.
- **Rhythm:** An 8px linear scale governs all padding and margins. 
- **Density:** The design leans toward "Low Density." Use large internal padding (`glass-padding`) within containers to give AI-generated insights room to "breathe."
- **Responsiveness:** On mobile, margins shrink to 20px, and the multi-column dashboard reflows into a single vertical stack. The sidebar transitions into a bottom-sheet or a full-screen glass overlay.

## Elevation & Depth

Depth is achieved through a "Stacked Glass" metaphor rather than traditional dark shadows.

1.  **Base Layer:** The warm Beige background (#F8F4E9).
2.  **Surface Layer:** Large containers (like the main workspace) use a subtle white semi-transparent fill with a 30px backdrop blur. Borders are 1px, solid white at 50% opacity, creating a "light-catching" edge.
3.  **Floating Layer:** Modals and tooltips use a slightly more opaque glass fill with a soft, ultra-diffused shadow (Blur: 40px, Spread: -10px, Color: Primary at 10% opacity) to suggest they are hovering higher above the base.
4.  **Active Elements:** Buttons and interactive cards should use a subtle inner glow (inner shadow) to appear slightly recessed or "carved" when active, maintaining the tactile macOS aesthetic.

## Shapes

The shape language is defined by oversized, friendly radiuses that mimic premium hardware. 

- **Containers:** Main dashboard panels and "glass" cards use a **24px** corner radius.
- **Buttons & Inputs:** Interactive elements use a **12px** radius, providing a distinct visual difference from the containers they sit within.
- **Consistency:** Avoid pill-shaped buttons; the squared-off but soft 12px radius maintains the professional SaaS tone while remaining approachable.

## Components

### Buttons
- **Primary:** Solid Deep Violet (#502D55) with White text. Use a very subtle 1px top-border in a lighter violet to simulate a light source.
- **Secondary:** Transparent glass base with a 1px Muted Plum border.
- **Motion:** On hover, primary buttons should scale up by 2% (1.02x) with a smooth 300ms cubic-bezier transition.

### Cards & Modules (Analysis Panels)
Following the sketch, the "Fruit Spotlight" and "Analysis" sections are housed in glass cards. Each card features a 1px white border and a 24px radius. Content inside should be padded by at least 32px.

### Input Fields
Inputs are "hollow" with a 1px border of Muted Plum at 30% opacity. Upon focus, the border opacity increases to 100% and the background gains a very subtle Creamy Sand (#F6DBC0) tint.

### Sidebar (History/Navigation)
The sidebar should be a continuous vertical pane of frosted glass. Navigation items use the Secondary color (#935073) for active states with a small vertical indicator bar on the left.

### AI Progress/Loading
Use "shimmer" effects rather than spinning wheels. A soft gradient of Creamy Sand and Muted Plum should pulse across the glass containers while the AI is "Analyzing..."