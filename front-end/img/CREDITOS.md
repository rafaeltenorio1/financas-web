# Créditos dos ícones de marcas

`marcas.svg` junta ícones de duas fontes. As marcas pertencem às suas empresas e aparecem aqui só para identificar onde cada transação aconteceu.

- **Simple Icons** 13.21.0 (https://simpleicons.org), licença CC0 1.0. Símbolos sem prefixo (por exemplo, `uber`, `netflix`).
- **Arcticons** 1.2.20, de Donnnno e colaboradores (https://github.com/Arcticons-Team/Arcticons), licença CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/). Símbolos com prefixo `t-` (por exemplo, `t-santander`), com a espessura do traço ajustada. Por causa da licença, esses símbolos continuam sob CC BY-SA 4.0.

As marcas sem ícone nas duas fontes aparecem como iniciais na cor da marca (monograma), sem usar arte de terceiros.

Para gerar de novo `marcas.svg` e `js/marcas.js`: baixe `simple-icons@13.21.0` (npm) e `@iconify-json/arcticons@1.2.20` (`icons.json`) e rode `python3 -I ferramentas/gerar_marcas.py <pasta do simple-icons> <icons.json do arcticons> front-end`.
