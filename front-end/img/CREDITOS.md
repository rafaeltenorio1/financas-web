# Créditos dos ícones de marcas

`marcas.svg` junta ícones de duas fontes. As marcas pertencem às suas empresas e aparecem aqui só para identificar onde cada transação aconteceu.

- **Simple Icons** 13.21.0 (https://simpleicons.org), licença CC0 1.0. Símbolos sem prefixo (por exemplo, `uber`, `netflix`).
- **Arcticons** 1.2.20, de Donnnno e colaboradores (https://github.com/Arcticons-Team/Arcticons), licença CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/). Símbolos com prefixo `t-` (por exemplo, `t-santander`), com a espessura do traço ajustada. Por causa da licença, esses símbolos continuam sob CC BY-SA 4.0.

As marcas sem ícone nas duas fontes aparecem como iniciais na cor da marca (monograma), sem usar arte de terceiros.

Para gerar de novo `marcas.svg` e `js/marcas.js`: baixe `simple-icons@13.21.0` (npm) e `@iconify-json/arcticons@1.2.20` (`icons.json`) e rode `python3 -I ferramentas/gerar_marcas.py <pasta do simple-icons> <icons.json do arcticons> front-end`.

# Bibliotecas copiadas

- **qrcode-generator** 1.4.4, de Kazuhiko Arase (https://github.com/kazuhikoarase/qrcode-generator), licença MIT (o aviso está no cabeçalho do arquivo). Copiado sem alterações em `js/vendor/qrcode-generator-1.4.4.js` (SHA-256 `18ae399f81182bc9de916e9c77b195df20cc58d6f2d55a62b085a299f1bf1780`). O QR é desenhado por `js/qr.js` com o DOM, sem o `createSvgTag` da biblioteca.
