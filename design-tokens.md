# Globalsys — Design Tokens

Extraído do site oficial (globalsys.com.br). Referência de identidade visual pra qualquer implementação (web, mobile, dashboard).

## Cores

| Token | Hex | Uso |
|---|---|---|
| `--gs-navy-900` | `#041833` | Início do gradiente de marca |
| `--gs-blue-800` | `#0000AA` | Gradiente de marca / início do gradiente de botão |
| `--gs-blue-700` | `#1D1DDB` | Meio do gradiente de marca |
| `--gs-blue-600` | `#0F0FC3` | Gradiente de marca |
| `--gs-navy-950` | `#00083D` | Fim do gradiente de marca |
| `--gs-blue-accent` | `#0156FC` | Azul de destaque — links, títulos em fundo claro, fim do gradiente de botão |
| `--gs-text` | `#000A1E` | Texto principal sobre fundo claro (quase preto, puxado pro azul-marinho — nunca usar `#000000` puro) |
| `--gs-white` | `#FFFFFF` | Texto/ícones sobre fundo escuro |
| `--gs-bg-alt` | `#FAF9F5` | Fundo alternativo off-white |
| `--gs-cyan-accent` | `#00F3FF` | Acento pontual (glow), usar com moderação — opacidade ~85% |
| `--gs-border` | `rgba(0, 10, 30, 0.1)` | Borda sutil de cards/superfícies |

**Gradiente de marca** (headers, footers, superfícies principais):
```css
background: linear-gradient(112.61deg, #041833 0%, #0000AA 24%, #1D1DDB 62%, #0F0FC3 81%, #00083D 100%);
```

**Gradiente de botão/CTA** (botões primários, ícones de destaque):
```css
background: linear-gradient(90deg, #0000AA 0%, #0156FC 100%);
```

## Tipografia

- **Títulos** (headings, nomes de destaque, texto de botão): `Space Grotesk` — peso 700 (bold) para títulos, 600 (semibold) para botões.
- **Corpo/texto corrido**: `Montserrat` — peso 400 (regular), tamanhos entre 13–17px conforme contexto, line-height ~1.5.

Google Fonts (import):
```
https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600&family=Space+Grotesk:wght@600;700&display=swap
```

## Raios e bordas

| Elemento | Border-radius |
|---|---|
| Cards / painéis | `20px` |
| Botões / inputs (pílula) | `50px` |
| Elementos circulares (avatares, FAB) | `50%` |
| Bordas de superfície | `1px solid rgba(0,10,30,0.1)` — sem sombra forte em cards estáticos; `box-shadow` só em elementos flutuantes (FAB, painéis overlay) |

## CSS pronto pra colar (`:root`)

```css
:root {
  --gs-navy-900: #041833;
  --gs-blue-800: #0000AA;
  --gs-blue-700: #1D1DDB;
  --gs-blue-600: #0F0FC3;
  --gs-navy-950: #00083D;
  --gs-blue-accent: #0156FC;
  --gs-text: #000A1E;
  --gs-white: #FFFFFF;
  --gs-bg-alt: #FAF9F5;
  --gs-cyan-accent: #00F3FF;
  --gs-border: rgba(0, 10, 30, 0.1);

  --gs-gradient-brand: linear-gradient(112.61deg, #041833 0%, #0000AA 24%, #1D1DDB 62%, #0F0FC3 81%, #00083D 100%);
  --gs-gradient-cta: linear-gradient(90deg, #0000AA 0%, #0156FC 100%);

  --gs-font-heading: 'Space Grotesk', sans-serif;
  --gs-font-body: 'Montserrat', sans-serif;

  --gs-radius-card: 20px;
  --gs-radius-pill: 50px;
}
```

## JSON (pra uso programático / theme config)

```json
{
  "color": {
    "navy900": "#041833",
    "blue800": "#0000AA",
    "blue700": "#1D1DDB",
    "blue600": "#0F0FC3",
    "navy950": "#00083D",
    "blueAccent": "#0156FC",
    "text": "#000A1E",
    "white": "#FFFFFF",
    "bgAlt": "#FAF9F5",
    "cyanAccent": "#00F3FF",
    "border": "rgba(0, 10, 30, 0.1)"
  },
  "gradient": {
    "brand": "linear-gradient(112.61deg, #041833 0%, #0000AA 24%, #1D1DDB 62%, #0F0FC3 81%, #00083D 100%)",
    "cta": "linear-gradient(90deg, #0000AA 0%, #0156FC 100%)"
  },
  "font": {
    "heading": "Space Grotesk",
    "body": "Montserrat"
  },
  "radius": {
    "card": "20px",
    "pill": "50px"
  }
}
```
