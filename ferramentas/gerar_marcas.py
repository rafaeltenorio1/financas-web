import json, re, sys, unicodedata
from pathlib import Path

pacote, arcticons_json, front = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])

def slug(t):
    t = t.lower().replace("+", "plus").replace(".", "dot").replace("&", "and")
    t = unicodedata.normalize("NFD", t)
    return re.sub(r"[^a-z0-9]", "", t)

hexes = {(i.get("slug") or slug(i["title"])): i["hex"] for i in json.load(open(pacote / "_data/simple-icons.json"))["icons"]}
arc = json.load(open(arcticons_json))["icons"]

A = {
 "uber": ["uber"], "ubereats": ["uber eats", "ubereats"], "lyft": ["lyft"], "shell": ["shell"],
 "americanairlines": ["american airlines", "aa com"], "delta": ["delta air", "delta airlines"], "unitedairlines": ["united airlines"],
 "emirates": ["emirates"], "qatarairways": ["qatar airways"], "airfrance": ["air france"], "klm": ["klm"], "lufthansa": ["lufthansa"],
 "iberia": ["iberia"], "turkishairlines": ["turkish airlines"], "ryanair": ["ryanair"], "easyjet": ["easyjet"], "avianca": ["avianca"],
 "copaairlines": ["copa airlines"], "jetblue": ["jetblue"], "airbnb": ["airbnb"], "hotelsdotcom": ["hotels com"], "expedia": ["expedia"],
 "tripadvisor": ["tripadvisor"], "trivago": ["trivago"], "marriott": ["marriott"], "hilton": ["hilton"], "dhl": ["dhl"], "fedex": ["fedex"], "ups": ["ups"],
 "ifood": ["ifood", "ifd"], "doordash": ["doordash"], "grubhub": ["grubhub"], "deliveroo": ["deliveroo"], "justeat": ["just eat", "justeat"],
 "glovo": ["glovo"], "foodpanda": ["foodpanda"], "swiggy": ["swiggy"], "zomato": ["zomato"], "instacart": ["instacart"],
 "hellofresh": ["hellofresh", "hello fresh"], "mcdonalds": ["mcdonalds", "mc donalds", "mcdonald s", "mequi"], "burgerking": ["burger king"],
 "kfc": ["kfc"], "starbucks": ["starbucks"], "tacobell": ["taco bell"], "cocacola": ["coca cola", "cocacola"], "redbull": ["red bull", "redbull"],
 "amazon": ["amazon", "amzn"], "shopee": ["shopee"], "aliexpress": ["aliexpress"], "alibabadotcom": ["alibaba"], "ebay": ["ebay"], "etsy": ["etsy"],
 "ikea": ["ikea"], "leroymerlin": ["leroy merlin"], "carrefour": ["carrefour"], "walmart": ["walmart"], "lidl": ["lidl"], "auchan": ["auchan"],
 "tesco": ["tesco"], "intermarche": ["intermarche"], "target": ["target"], "macys": ["macys", "macy s"], "zara": ["zara"], "uniqlo": ["uniqlo"],
 "nike": ["nike"], "adidas": ["adidas"], "puma": ["puma"], "reebok": ["reebok"], "newbalance": ["new balance"], "underarmour": ["under armour"],
 "zalando": ["zalando"], "farfetch": ["farfetch"], "dior": ["dior"],
 "apple": ["apple", "apple com"], "samsung": ["samsung"], "xiaomi": ["xiaomi"], "motorola": ["motorola"], "lg": ["lg", "lg electronics"],
 "sony": ["sony"], "dell": ["dell"], "hp": ["hp", "hp inc"], "lenovo": ["lenovo"], "asus": ["asus"], "acer": ["acer"], "logitech": ["logitech"],
 "razer": ["razer"], "nvidia": ["nvidia", "geforce now"], "beatsbydre": ["beats by dre"], "bose": ["bose"], "jbl": ["jbl"], "nikon": ["nikon"],
 "dji": ["dji"], "philipshue": ["philips hue"], "oppo": ["oppo"], "oneplus": ["oneplus", "one plus"], "huawei": ["huawei"],
 "garmin": ["garmin"], "fitbit": ["fitbit"],
 "steam": ["steam", "steampowered", "steam games"], "epicgames": ["epic games", "epicgames"], "riotgames": ["riot games", "riot"],
 "leagueoflegends": ["league of legends"], "valorant": ["valorant"], "battledotnet": ["battle net", "blizzard"], "ubisoft": ["ubisoft"],
 "roblox": ["roblox"], "gogdotcom": ["gog com"], "rockstargames": ["rockstar games"], "playstation": ["playstation", "psn", "playstation network"],
 "nintendo": ["nintendo", "nintendo eshop"], "itchdotio": ["itch io"], "humblebundle": ["humble bundle"], "pokemon": ["pokemon"],
 "netflix": ["netflix"], "spotify": ["spotify"], "tidal": ["tidal"], "applemusic": ["apple music"], "youtube": ["youtube", "youtube premium"],
 "youtubemusic": ["youtube music"], "primevideo": ["prime video", "primevideo", "amazon prime video"], "amazonprime": ["amazon prime"],
 "hbo": ["hbo"], "max": ["hbo max", "hbomax", "max com"], "paramountplus": ["paramount", "paramount plus"], "crunchyroll": ["crunchyroll"],
 "twitch": ["twitch"], "appletv": ["apple tv"], "mubi": ["mubi"], "vimeo": ["vimeo"], "dazn": ["dazn"], "fubo": ["fubo", "fubotv"],
 "funimation": ["funimation"], "starz": ["starz"], "showtime": ["showtime"], "audible": ["audible"], "scribd": ["scribd"],
 "soundcloud": ["soundcloud"], "pandora": ["pandora"], "plex": ["plex"], "applearcade": ["apple arcade"], "icloud": ["icloud"],
 "googleplay": ["google play"], "googledrive": ["google drive", "google one", "google storage"], "dropbox": ["dropbox"],
 "adobe": ["adobe"], "adobecreativecloud": ["creative cloud"], "canva": ["canva"], "notion": ["notion so", "notion labs"],
 "evernote": ["evernote"], "1password": ["1password"], "bitwarden": ["bitwarden"], "lastpass": ["lastpass"], "nordvpn": ["nordvpn", "nord vpn"],
 "expressvpn": ["expressvpn"], "surfshark": ["surfshark"], "protonvpn": ["proton vpn", "protonvpn"], "protonmail": ["proton mail", "protonmail", "proton ag"],
 "openai": ["openai", "chatgpt"], "claude": ["claude ai", "claude"], "anthropic": ["anthropic"], "googlegemini": ["google gemini", "gemini advanced"],
 "perplexity": ["perplexity"], "githubcopilot": ["github copilot"], "github": ["github"], "discord": ["discord"], "telegram": ["telegram"],
 "zoom": ["zoom us", "zoom video", "zoom com"], "linkedin": ["linkedin"], "tinder": ["tinder"], "patreon": ["patreon"], "onlyfans": ["onlyfans"],
 "kickstarter": ["kickstarter"], "gofundme": ["gofundme"], "buymeacoffee": ["buy me a coffee", "buymeacoffee"], "kofi": ["ko fi", "kofi"],
 "duolingo": ["duolingo"], "coursera": ["coursera"], "udemy": ["udemy"], "khanacademy": ["khan academy"], "skillshare": ["skillshare"],
 "wikipedia": ["wikipedia", "wikimedia"], "ticketmaster": ["ticketmaster"], "eventbrite": ["eventbrite"], "strava": ["strava"],
 "peloton": ["peloton"], "headspace": ["headspace"], "facebook": ["facebook", "facebk"], "instagram": ["instagram"], "tiktok": ["tiktok"],
 "pinterest": ["pinterest"], "reddit": ["reddit"], "snapchat": ["snapchat"], "google": ["google"],
 "nubank": ["nubank", "nu pagamentos"], "picpay": ["picpay"], "pagseguro": ["pagseguro", "pagbank", "pag seguro"],
 "mercadopago": ["mercado pago", "mercadopago"], "paypal": ["paypal"], "wise": ["wise com", "transferwise"], "revolut": ["revolut"],
 "n26": ["n26"], "monzo": ["monzo"], "binance": ["binance"], "coinbase": ["coinbase"], "nomad": ["nomad"], "pix": ["pix"],
 "applepay": ["apple pay"], "googlepay": ["google pay"], "samsungpay": ["samsung pay"], "alipay": ["alipay"], "wechat": ["wechat"],
 "visa": ["visa"], "mastercard": ["mastercard"], "americanexpress": ["american express", "amex"], "klarna": ["klarna"],
 "afterpay": ["afterpay"], "payoneer": ["payoneer"], "westernunion": ["western union"], "hsbc": ["hsbc"], "barclays": ["barclays"],
 "chase": ["chase"], "bankofamerica": ["bank of america"], "wellsfargo": ["wells fargo"], "amazonpay": ["amazon pay"],
 "vivo": ["=vivo", "vivo fibra", "vivo movel", "vivo pos", "vivo controle", "vivo internet", "vivo celular", "conta vivo", "telefonica"],
 "vodafone": ["vodafone"], "tmobile": ["t mobile", "tmobile"], "verizon": ["verizon"], "atandt": ["at t", "att"], "movistar": ["movistar"],
 "toyota": ["toyota"], "honda": ["honda"], "volkswagen": ["volkswagen", "vw"], "fiat": ["fiat"], "chevrolet": ["chevrolet"], "ford": ["ford"],
 "hyundai": ["hyundai"], "renault": ["renault"], "nissan": ["nissan"], "jeep": ["jeep"], "bmw": ["bmw"], "mercedes": ["mercedes benz"],
 "audi": ["audi"], "tesla": ["tesla"], "peugeot": ["peugeot"], "citroen": ["citroen"], "kia": ["kia"], "mitsubishi": ["mitsubishi"],
 "suzuki": ["suzuki"], "volvo": ["volvo"], "porsche": ["porsche"], "lamborghini": ["lamborghini"], "landrover": ["land rover"],
 "jaguar": ["jaguar"], "mazda": ["mazda"], "subaru": ["subaru"], "dacia": ["dacia"], "skoda": ["skoda"], "ducati": ["ducati"],
}

B = {
 "mercado-libre": ("#ffe600", "#2d3277", ["mercado livre", "mercadolivre", "mercadolibre"]),
 "99": ("#ffdd00", "#000000", ["99app", "99 app", "99 pop", "99pop", "99 taxi", "99 tecnologia", "=99"]),
 "santander": ("#ec0000", "#ffffff", ["santander"]),
 "caixa": ("#005ca9", "#ffffff", ["caixa economica", "caixa federal", "caixa tem", "=caixa"]),
 "inter": ("#ff7a00", "#ffffff", ["banco inter", "inter co", "=inter"]),
 "c6bank": ("#242424", "#ffffff", ["c6 bank", "c6bank", "banco c6"]),
 "neon": ("#00a5e0", "#ffffff", ["banco neon", "neon pagamentos"]),
 "sicoob": ("#003641", "#ffffff", ["sicoob"]),
 "xp-investimentos": ("#000000", "#ffffff", ["xp investimentos", "xp inc"]),
 "rico": ("#ff6b00", "#ffffff", ["rico investimentos", "rico corretora"]),
 "recargapay": ("#0069ff", "#ffffff", ["recargapay"]),
 "meliuz": ("#ea0d5e", "#ffffff", ["meliuz"]),
 "smiles": ("#ff7020", "#ffffff", ["smiles"]),
 "claro": ("#da291c", "#ffffff", ["=claro", "claro sa", "claro tv", "claro net", "net claro", "claro movel", "claro celular", "claro internet"]),
 "tim": ("#004b9b", "#ffffff", ["=tim", "tim celular", "tim brasil", "tim s a", "tim sa", "tim controle", "tim pre", "tim black", "tim live"]),
 "rappi": ("#ff441f", "#ffffff", ["rappi"]),
 "aiqfome": ("#7b1fa2", "#ffffff", ["aiqfome"]),
 "subway": ("#008938", "#ffffff", ["subway"]),
 "dominos": ("#006491", "#ffffff", ["dominos", "domino s"]),
 "pizzahut": ("#c8102e", "#ffffff", ["pizza hut"]),
 "disney": ("#0f1a5c", "#ffffff", ["disney"]),
 "globoplay": ("#fb0234", "#ffffff", ["globoplay", "globo play"]),
 "deezer": ("#a238ff", "#ffffff", ["deezer"]),
 "microsoft": ("#2f2f2f", "#ffffff", ["microsoft", "msft", "office 365", "microsoft 365"]),
 "xbox": ("#107c10", "#ffffff", ["xbox", "game pass"]),
 "booking": ("#003580", "#ffffff", ["booking com", "booking"]),
 "magalu": ("#0086ff", "#ffffff", ["magalu", "magazine luiza", "magazineluiza"]),
 "americanas": ("#e60014", "#ffffff", ["americanas", "lojas americanas"]),
 "casas-bahia": ("#1f3fd4", "#ffffff", ["casas bahia", "casasbahia"]),
 "shein": ("#000000", "#ffffff", ["shein"]),
 "temu": ("#fb7701", "#ffffff", ["temu"]),
 "netshoes": ("#4c1d81", "#ffffff", ["netshoes"]),
 "enjoei": ("#f0487d", "#ffffff", ["enjoei"]),
 "olx": ("#6e0ad6", "#ffffff", ["=olx", "olx brasil", "olx pay"]),
 "correios": ("#ffd400", "#00416b", ["correios", "sedex"]),
 "smart-fit": ("#ffb612", "#000000", ["smart fit", "smartfit"]),
 "ingressocom": ("#e10b34", "#ffffff", ["ingresso com", "ingressocom"]),
 "cinemark-theatres": ("#ed1c24", "#ffffff", ["cinemark"]),
 "cabify": ("#7145d6", "#ffffff", ["cabify"]),
 "indriver": ("#c1f11d", "#000000", ["indriver", "indrive"]),
}

C = {
 "bb": ("BB", "#fcfc30", "#465eff", ["banco do brasil", "bb banco", "=bb"]),
 "itau": ("itaú", "#ec7000", "#ffffff", ["itau", "itaucard", "itau unibanco", "banco itau"]),
 "bradesco": ("B", "#cc092f", "#ffffff", ["bradesco", "bradescard"]),
 "btg": ("btg", "#0b1f41", "#ffffff", ["btg pactual", "btg"]),
 "pan": ("pan", "#00b1e6", "#ffffff", ["banco pan"]),
 "sicredi": ("S", "#3fa110", "#ffffff", ["sicredi"]),
 "banrisul": ("B", "#00539f", "#ffffff", ["banrisul"]),
 "digio": ("D", "#0a2e5c", "#ffffff", ["digio"]),
 "agibank": ("A", "#00a3e0", "#ffffff", ["agibank"]),
 "will": ("will", "#ffe000", "#000000", ["will bank", "willbank"]),
 "sky": ("sky", "#d0021b", "#ffffff", ["sky brasil", "sky tv", "=sky"]),
 "latam": ("L", "#1b0088", "#ffffff", ["latam", "tam linhas"]),
 "azul": ("A", "#0033a0", "#ffffff", ["azul linhas", "voe azul", "voeazul", "azul viagens", "tudo azul", "=azul"]),
 "gol": ("G", "#ff5a00", "#ffffff", ["gol linhas", "voe gol", "voegol", "=gol"]),
 "decolar": ("D", "#5c2d91", "#ffffff", ["decolar"]),
 "maxmilhas": ("M", "#0f4c81", "#ffffff", ["maxmilhas"]),
 "buser": ("B", "#ec4899", "#ffffff", ["buser"]),
 "clickbus": ("C", "#2b2b9b", "#ffffff", ["clickbus"]),
 "localiza": ("L", "#00953b", "#ffffff", ["localiza"]),
 "semparar": ("SP", "#da291c", "#ffffff", ["sem parar"]),
 "conectcar": ("C", "#00a04b", "#ffffff", ["conectcar"]),
 "veloe": ("V", "#2d2a83", "#ffffff", ["veloe"]),
 "ipiranga": ("I", "#ffcc00", "#003a70", ["ipiranga", "posto ipiranga"]),
 "petrobras": ("BR", "#008542", "#fddb00", ["petrobras", "posto br", "br distribuidora", "vibra energia"]),
 "drogasil": ("D", "#e30613", "#ffffff", ["drogasil"]),
 "raia": ("R", "#0062a6", "#ffffff", ["droga raia", "drogaraia", "=raia"]),
 "paguemenos": ("PM", "#003c8f", "#ffffff", ["pague menos"]),
 "panvel": ("P", "#003da5", "#ffffff", ["panvel"]),
 "unimed": ("U", "#00995d", "#ffffff", ["unimed"]),
 "hapvida": ("H", "#f26522", "#ffffff", ["hapvida"]),
 "amil": ("A", "#00529c", "#ffffff", ["=amil", "amil saude"]),
 "wellhub": ("W", "#d8385e", "#ffffff", ["wellhub", "gympass"]),
 "totalpass": ("T", "#111111", "#ffffff", ["totalpass"]),
 "natura": ("N", "#f47920", "#ffffff", ["natura"]),
 "boticario": ("oB", "#00704a", "#ffffff", ["boticario"]),
 "renner": ("R", "#e3001b", "#ffffff", ["renner"]),
 "riachuelo": ("R", "#1d1d1b", "#ffffff", ["riachuelo"]),
 "cea": ("C&A", "#0052a5", "#ffffff", ["c a modas", "=c a", "cea modas"]),
 "marisa": ("M", "#e5007e", "#ffffff", ["lojas marisa", "=marisa"]),
 "hering": ("H", "#0033a1", "#ffffff", ["hering"]),
 "havaianas": ("H", "#ffcc00", "#000000", ["havaianas"]),
 "arezzo": ("A", "#1d1d1b", "#ffffff", ["arezzo"]),
 "vivara": ("V", "#1d1d1b", "#ffffff", ["vivara"]),
 "centauro": ("C", "#e30613", "#ffffff", ["centauro"]),
 "dafiti": ("D", "#1d1d1b", "#ffffff", ["dafiti"]),
 "kabum": ("K", "#0060b1", "#ffffff", ["kabum"]),
 "fastshop": ("FS", "#e30613", "#ffffff", ["fast shop", "fastshop"]),
 "pontofrio": ("P", "#1d1d1b", "#ffffff", ["ponto frio", "pontofrio"]),
 "submarino": ("S", "#0071bc", "#ffffff", ["submarino"]),
 "shoptime": ("S", "#e6007e", "#ffffff", ["shoptime"]),
 "tokstok": ("T", "#1d1d1b", "#ffffff", ["tok stok", "tokstok"]),
 "mobly": ("M", "#ff6900", "#ffffff", ["mobly"]),
 "madeiramadeira": ("MM", "#ff6a13", "#ffffff", ["madeira madeira", "madeiramadeira"]),
 "paodeacucar": ("PA", "#00843d", "#ffffff", ["pao de acucar"]),
 "assai": ("A", "#f26c21", "#ffffff", ["assai"]),
 "atacadao": ("A", "#e30613", "#ffffff", ["atacadao"]),
 "zedelivery": ("Zé", "#ffc600", "#000000", ["ze delivery", "zedelivery"]),
 "outback": ("O", "#7a1712", "#ffffff", ["outback"]),
 "habibs": ("H", "#e30613", "#ffffff", ["habib s", "habibs"]),
 "bobs": ("B", "#e30613", "#ffffff", ["bobs", "bob s"]),
 "cinepolis": ("C", "#0a2a5c", "#ffffff", ["cinepolis"]),
 "sympla": ("S", "#1d1d1b", "#ffffff", ["sympla"]),
 "livelo": ("L", "#e6007e", "#ffffff", ["livelo"]),
 "dotz": ("D", "#ff5a00", "#ffffff", ["dotz"]),
 "enel": ("E", "#0555fa", "#ffffff", ["enel"]),
 "cpfl": ("CPFL", "#00a1e1", "#ffffff", ["cpfl"]),
 "cemig": ("C", "#007a3d", "#ffffff", ["cemig"]),
 "light": ("L", "#f15a22", "#ffffff", ["light sa", "light servicos", "=light"]),
 "copel": ("C", "#0071bc", "#ffffff", ["copel"]),
 "sabesp": ("S", "#0072bc", "#ffffff", ["sabesp"]),
 "copasa": ("C", "#0066b3", "#ffffff", ["copasa"]),
 "comgas": ("C", "#0071bc", "#ffffff", ["comgas"]),
}

def lum(h):
    c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

TAGS = {"path", "circle", "ellipse", "rect", "line", "polyline", "polygon", "g"}
ATRIBUTOS = {"d", "cx", "cy", "r", "rx", "ry", "x", "y", "x1", "y1", "x2", "y2", "width", "height", "points", "fill",
             "stroke", "stroke-linecap", "stroke-linejoin", "stroke-width", "transform", "fill-rule", "clip-rule"}
VALOR_SEGURO = re.compile(r"[0-9A-Za-z .,\-#()]*")

def corpo_seguro(corpo):
    for tag, attrs in re.findall(r"<\s*/?\s*([a-zA-Z]+)([^>]*)>", corpo):
        if tag not in TAGS:
            raise ValueError(f"tag {tag}")
        for nome, valor in re.findall(r'([a-zA-Z:-]+)="([^"]*)"', attrs):
            if nome not in ATRIBUTOS or not VALOR_SEGURO.fullmatch(valor):
                raise ValueError(f"atributo {nome}")
        resto = re.sub(r'([a-zA-Z:-]+)="([^"]*)"', "", attrs).strip().rstrip("/").strip()
        if resto:
            raise ValueError("atributo sem aspas")
    return corpo.replace('stroke-linecap', 'stroke-width="2.6" stroke-linecap')

simbolos, linhas, faltando, usadas = [], [], [], set()
todas_chaves = {}

def registrar(id_, chaves):
    for ch in chaves:
        if ch in todas_chaves:
            raise ValueError(f"chave repetida {ch!r} em {id_} e {todas_chaves[ch]}")
        todas_chaves[ch] = id_

for s, chaves in A.items():
    arq = pacote / "icons" / f"{s}.svg"
    if not arq.exists() or s not in hexes:
        faltando.append(s); continue
    caminho = re.search(r'<path d="([^"]+)"', arq.read_text()).group(1)
    if not re.fullmatch(r"[0-9A-Za-z .,\-]+", caminho):
        faltando.append(s); continue
    fundo = "#" + hexes[s].lower()
    cor = "#000000" if (lum(hexes[s]) + 0.05) / 0.05 > 1.05 / (lum(hexes[s]) + 0.05) else "#ffffff"
    simbolos.append(f'<symbol id="{s}" viewBox="0 0 24 24"><path fill="currentColor" d="{caminho}"/></symbol>')
    linhas.append(f'  ["{s}", "{fundo}", "{cor}", {json.dumps(chaves, ensure_ascii=False)}],')
    registrar(s, chaves); usadas.add(s)

for nome, (fundo, cor, chaves) in B.items():
    if nome not in arc:
        faltando.append("t-" + nome); continue
    try:
        corpo = corpo_seguro(arc[nome]["body"])
    except ValueError as erro:
        faltando.append(f"t-{nome} ({erro})"); continue
    id_ = "t-" + nome
    simbolos.append(f'<symbol id="{id_}" viewBox="0 0 48 48">{corpo}</symbol>')
    linhas.append(f'  ["{id_}", "{fundo}", "{cor}", {json.dumps(chaves, ensure_ascii=False)}, "traco"],')
    registrar(id_, chaves)

for nome, (texto, fundo, cor, chaves) in C.items():
    id_ = "m-" + nome
    linhas.append(f'  ["{id_}", "{fundo}", "{cor}", {json.dumps(chaves, ensure_ascii=False)}, "monograma", {json.dumps(texto, ensure_ascii=False)}],')
    registrar(id_, chaves)

(front / "img/marcas.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg">' + "".join(simbolos) + "</svg>\n")

js = '''const MARCAS = [
''' + "\n".join(linhas) + '''
];

function normalizar(texto) {
  return ` ${String(texto)
    .normalize("NFD")
    .replace(/[\\u0300-\\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()} `;
}

const CHAVES = MARCAS.flatMap(([id, fundo, cor, chaves, estilo = "logo", texto = null]) =>
  chaves.map((bruta) => {
    const exata = bruta.startsWith("=");
    const chave = exata ? bruta.slice(1) : bruta;
    return {
      chave: ` ${chave} `,
      compacta: !exata && chave.includes(" ") ? ` ${chave.replaceAll(" ", "")} ` : null,
      exata,
      marca: { id, fundo, cor, estilo, texto },
    };
  }),
).sort((a, b) => b.chave.length - a.chave.length);

export function marcaDe(nome) {
  if (!nome) return null;
  const alvo = normalizar(nome);
  for (const { chave, compacta, exata, marca } of CHAVES) {
    if (exata ? alvo === chave : alvo.includes(chave) || (compacta && alvo.includes(compacta))) return marca;
  }
  return null;
}

export const QUANTIDADE_MARCAS = MARCAS.length;
'''
(front / "js/marcas.js").write_text(js)
print("logo:", len(usadas), "traço:", sum(1 for l in linhas if '"traco"' in l), "monograma:", len(C), "faltando:", faltando)
