import { useState } from "react";

const C = {
  bleu: "#1A3A5C", bleuF: "#0F2237", or: "#C9A84C", orC: "#E8C76A",
  vert: "#1A6B45", vertC: "#2ECC71", rouge: "#C0392B",
  fond: "#0A0F1A", card: "#0F1923", border: "#1E2D3D",
  texte: "#E8EDF2", sub: "#8FA3B8",
};

const LOGO_SVG = `<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#1A3A5C"/><stop offset="100%" stop-color="#0F2237"/>
  </linearGradient></defs>
  <rect width="80" height="80" rx="18" fill="url(#g)"/>
  <text x="40" y="55" font-family="Arial Black" font-size="46" fill="#C9A84C" text-anchor="middle" font-weight="900">A</text>
  <rect x="14" y="62" width="52" height="4" rx="2" fill="#C9A84C" opacity="0.5"/>
</svg>`;

const PALETTE = [
  { hex:"#1A3A5C", name:"Bleu profond",   role:"Fond principal, navbar" },
  { hex:"#C9A84C", name:"Or Bukavu",      role:"Accents, CTA, logos" },
  { hex:"#1A6B45", name:"Vert AVEC",      role:"Succès, épargne" },
  { hex:"#C0392B", name:"Rouge alerte",   role:"Retards, erreurs" },
  { hex:"#E8EDF2", name:"Blanc cassé",    role:"Texte principal" },
  { hex:"#0A0F1A", name:"Nuit profonde",  role:"Fond app" },
];

const STRUCTURE = {
  "akibacore/": {
    "package.json": "Monorepo root",
    "desktop/": {
      "package.json": "Electron + electron-builder",
      "src/main/": {
        "main.js": "Main process Electron",
        "server.js": "Factory Express",
        "database.js": "SQLite + schéma",
        "logger.js": "Winston logs",
        "middleware/auth.js": "Auth + audit",
        "routes/auth.js": "Login/logout",
        "routes/membres.js": "CRUD membres",
        "routes/operations.js": "Épargnes/crédits/rembs",
        "finance.js": "Calculs financiers",
      },
      "src/preload/preload.js": "contextBridge sécurisé",
      "src/renderer/": {
        "index.html": "Shell SPA",
        "login.html": "Écran connexion",
        "css/app.css": "Styles complets",
        "js/app.js": "SPA Vanilla JS",
      },
      "build/": { "icons/": "ico + png", "installer.nsh": "NSIS custom", "license.txt": "Licence FR" },
      "scripts/": { "setup.js": "Init", "backup.js": "Sauvegarde", "test.js": "Tests unitaires" },
    },
    "mobile/": {
      "package.json": "React Native 0.73",
      "App.js": "Navigation + thème",
      "src/db/database.js": "SQLite mobile",
      "src/screens/": {
        "Dashboard.js": "Tableau de bord",
        "Membres.js": "Liste membres",
        "Epargnes.js": "Dépôts",
        "Credits.js": "Prêts",
        "Remboursements.js": "Paiements",
        "Sync.js": "Wi-Fi sync",
      },
      "src/sync/SyncService.js": "Client sync Wi-Fi",
      "android/": "Build config APK",
    },
    "sync/": {
      "sync-server.js": "Serveur Wi-Fi local",
      "usb-export.js": "Export/Import USB JSON",
    },
    "docs/": { "INSTALLATION.md": "Guide complet" },
  }
};

const CODE_SAMPLES = {
  finance: `// finance.js — Calculs financiers (fonctions pures)
const interetSimple = (principal, tauxAnnuel, dureeMois) =>
  Math.round(principal * tauxAnnuel * (dureeMois / 12) * 100) / 100;

const imputerPaiement = (credit, montant, tauxPen = 0.02) => {
  const solde = credit.montant_total - credit.rembourse;
  const jr    = joursDeRetard(credit.date_echeance);
  const pen   = Math.min(jr > 0 ? penalite(solde, tauxPen, jr) : 0, montant);
  const reste = montant - pen;
  const ratI  = credit.montant_interet / credit.montant_total;
  const inter = Math.round(reste * ratI * 100) / 100;
  const princ = Math.round((reste - inter) * 100) / 100;
  const nouv  = Math.min(credit.rembourse + montant, credit.montant_total);
  return {
    pen, interet: inter, principal: princ,
    nouveauRembourse: nouv,
    nouveauStatut: nouv >= credit.montant_total ? 'solde'
                 : jr > 0 ? 'en_retard' : 'actif'
  };
};`,
  sync: `// sync-server.js — Synchronisation Wi-Fi local
app.post('/sync/import', verifKey, (req, res) => {
  const { membres=[], epargnes=[], credits=[] } = req.body;
  const stats = { membres:0, epargnes:0, conflits:0 };

  db.transaction(() => {
    for (const m of membres) {
      const existing = db.prepare(
        "SELECT * FROM membres WHERE uuid=?"
      ).get(m.uuid);

      if (!existing) {
        // Nouveau enregistrement mobile → desktop
        db.prepare(\`INSERT INTO membres(uuid,nom,prenom,...)\`)
          .run(m.uuid, m.nom, m.prenom, ...);
        stats.membres++;
      } else {
        // Résolution de conflit : LAST-WRITE-WINS
        const local  = new Date(existing.modifie_le);
        const remote = new Date(m.modifie_le);
        if (remote > local) {
          db.prepare("UPDATE membres SET nom=?,... WHERE uuid=?")
            .run(m.nom, ..., m.uuid);
        } else stats.conflits++;
      }
    }
  })();

  res.json({ ok:true, stats });
});`,
  mobile_db: `// mobile/src/db/database.js — SQLite React Native
export const MembresDB = {
  tous: (q='') => queryAll(\`
    SELECT m.*,
      COALESCE((SELECT SUM(montant) FROM epargnes
        WHERE membre_id=m.id AND annule=0),0) as epargne_totale,
      COALESCE((SELECT SUM(montant_total-rembourse) FROM credits
        WHERE membre_id=m.id AND statut IN ('actif','en_retard')),0) as credit_actif
    FROM membres m
    WHERE lower(m.nom||COALESCE(m.prenom,'')) LIKE ?
    ORDER BY m.nom\`,
    [\`%\${q.toLowerCase()}%\`]
  ),
  ajouter: (m) => execute(
    \`INSERT INTO membres(nom,prenom,telephone,nb_parts,synced)
      VALUES(?,?,?,?,0)\`,
    [m.nom, m.prenom, m.telephone, m.nb_parts||1]
  ),
};`,
  electron_main: `// main.js — Main Process Electron
app.whenReady().then(async () => {
  // 1. Démarrer Express en interne
  process.env.AKIBA_DATA_DIR = app.getPath('userData');
  const { createServer } = require('./server');
  server = createServer();
  server.listen(49152, '127.0.0.1');

  // 2. Créer la BrowserWindow
  mainWindow = new BrowserWindow({
    width: 1280, height: 800,
    webPreferences: {
      nodeIntegration:  false, // SÉCURITÉ
      contextIsolation: true,  // SÉCURITÉ
      sandbox: false,
      preload: path.join(__dirname, '../preload/preload.js'),
    },
  });

  // 3. Charger l'app locale (pas d'Internet !)
  mainWindow.loadURL('http://127.0.0.1:49152/login');

  // 4. Sauvegarde automatique toutes les 30 min
  setInterval(sauvegarder, 30 * 60 * 1000);
});`,
  schema_sql: `-- Schéma SQLite avec UUIDs pour la synchronisation
CREATE TABLE membres (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  uuid        TEXT UNIQUE DEFAULT (lower(hex(randomblob(16)))),
  nom         TEXT NOT NULL,
  prenom      TEXT, telephone TEXT, adresse TEXT,
  nb_parts    INTEGER DEFAULT 1 CHECK(nb_parts >= 1),
  statut      TEXT DEFAULT 'actif'
              CHECK(statut IN ('actif','suspendu','sorti')),
  date_adhesion TEXT DEFAULT (date('now','localtime')),
  synced      INTEGER DEFAULT 0, -- 0=non synced, 1=synced
  cree_le     TEXT DEFAULT (datetime('now','localtime')),
  modifie_le  TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE credits (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  uuid            TEXT UNIQUE DEFAULT (lower(hex(randomblob(16)))),
  membre_id       INTEGER NOT NULL,
  principal       REAL NOT NULL CHECK(principal > 0),
  taux            REAL NOT NULL CHECK(taux > 0 AND taux <= 1),
  montant_interet REAL NOT NULL,
  montant_total   REAL NOT NULL,
  rembourse       REAL DEFAULT 0,
  statut          TEXT DEFAULT 'actif'
                  CHECK(statut IN ('actif','solde','en_retard','annule')),
  FOREIGN KEY(membre_id) REFERENCES membres(id)
);

-- Index pour performances
CREATE INDEX idx_ep_membre ON epargnes(membre_id, annule);
CREATE INDEX idx_cr_statut ON credits(statut, date_echeance);`,
};

const INSTALL_STEPS = {
  desktop: [
    { n:"1", cmd:"git clone https://github.com/vous/akibacore.git && cd akibacore/desktop", desc:"Cloner le projet" },
    { n:"2", cmd:"npm install", desc:"Installer les dépendances Node.js" },
    { n:"3", cmd:"npm run dev", desc:"Tester en mode développement" },
    { n:"4", cmd:"npm run build", desc:"Générer AkibaCore Setup 2.0.0.exe" },
    { n:"5", cmd:"# → dist/AkibaCore Setup 2.0.0.exe", desc:"Distribuer via clé USB" },
  ],
  android: [
    { n:"1", cmd:"cd akibacore/mobile && npm install", desc:"Installer dépendances RN" },
    { n:"2", cmd:"npx react-native link react-native-sqlite-storage", desc:"Lier SQLite natif" },
    { n:"3", cmd:"cd android && ./gradlew assembleDebug", desc:"APK debug (test)" },
    { n:"4", cmd:"keytool -genkey -v -keystore akibacore.keystore -alias akibacore -keyalg RSA -keysize 2048 -validity 10000", desc:"Générer clé de signature" },
    { n:"5", cmd:"cd android && ./gradlew assembleRelease", desc:"APK production signé" },
  ],
  sync_wifi: [
    { n:"1", cmd:"cd akibacore/sync && node sync-server.js", desc:"Démarrer serveur (PC desktop)" },
    { n:"2", cmd:"# → IP locale : 192.168.x.x:7777", desc:"Note l'adresse affichée" },
    { n:"3", cmd:"# Sur le téléphone :", desc:"Connecter au même Wi-Fi" },
    { n:"4", cmd:"# App → Sync → Configurer → 192.168.x.x", desc:"Entrer l'IP du PC" },
    { n:"5", cmd:"# Clé : akiba-sync-2025 → Synchroniser", desc:"Lancer la synchronisation" },
  ],
  sync_usb: [
    { n:"1", cmd:"node sync/usb-export.js export D:\\", desc:"Exporter vers clé USB D:" },
    { n:"2", cmd:"# → D:\\akibacore_export_2025-XX-XX.json", desc:"Fichier JSON créé" },
    { n:"3", cmd:"# Sur l'autre PC :", desc:"Brancher la clé USB" },
    { n:"4", cmd:"node sync/usb-export.js import D:\\akibacore_export_XXX.json", desc:"Importer les données" },
  ],
};

function FileTree({ data, depth = 0 }) {
  const [open, setOpen] = useState(depth < 2);
  return (
    <div style={{ marginLeft: depth * 14 }}>
      {Object.entries(data).map(([k, v]) => {
        const isDir = typeof v === "object";
        return (
          <div key={k}>
            <div
              onClick={() => isDir && setOpen(!open)}
              style={{
                display:"flex", alignItems:"center", gap:6,
                padding:"3px 6px", borderRadius:4, cursor:isDir?"pointer":"default",
                color: isDir ? C.or : C.texte, fontSize:12,
                background: isDir && open ? "rgba(201,168,76,.06)" : "transparent",
              }}
            >
              <span style={{fontSize:11}}>{isDir ? (open ? "▼" : "▶") : "·"}</span>
              <span style={{fontFamily:"monospace"}}>{k}</span>
              {!isDir && <span style={{color:C.sub, fontSize:10, marginLeft:4}}>{v}</span>}
            </div>
            {isDir && open && <FileTree data={v} depth={depth + 1} />}
          </div>
        );
      })}
    </div>
  );
}

function CodeBlock({ code, lang = "js" }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard?.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div style={{ position:"relative", background:"#070D14", borderRadius:10, border:`1px solid ${C.border}` }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
        padding:"8px 14px", borderBottom:`1px solid ${C.border}` }}>
        <span style={{ color:C.or, fontSize:11, fontFamily:"monospace" }}>{lang}</span>
        <button onClick={copy} style={{
          background:"none", border:`1px solid ${C.border}`, color:C.sub,
          padding:"3px 10px", borderRadius:4, cursor:"pointer", fontSize:11,
        }}>{copied ? "✓ Copié" : "Copier"}</button>
      </div>
      <pre style={{ margin:0, padding:"14px 16px", overflowX:"auto",
        fontSize:11.5, lineHeight:1.7, color:"#B8D4F0", fontFamily:"'Courier New',monospace" }}>
        {code}
      </pre>
    </div>
  );
}

function Card({ children, style = {} }) {
  return (
    <div style={{
      background: C.card, border:`1px solid ${C.border}`,
      borderRadius:14, padding:"20px 22px", ...style,
    }}>{children}</div>
  );
}

function Badge({ children, color = C.or }) {
  return (
    <span style={{
      background:`${color}22`, color, border:`1px solid ${color}44`,
      padding:"2px 10px", borderRadius:20, fontSize:11, fontWeight:700,
    }}>{children}</span>
  );
}

function Pill({ icon, label, sub }) {
  return (
    <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:6,
      background:`${C.bleu}44`, border:`1px solid ${C.border}`,
      borderRadius:12, padding:"14px 18px", textAlign:"center", minWidth:90 }}>
      <span style={{ fontSize:22 }}>{icon}</span>
      <span style={{ color:C.texte, fontSize:12, fontWeight:700 }}>{label}</span>
      {sub && <span style={{ color:C.sub, fontSize:10 }}>{sub}</span>}
    </div>
  );
}

export default function AkibaCoreHub() {
  const [tab, setTab] = useState("apercu");
  const [codeTab, setCodeTab] = useState("finance");
  const [installTab, setInstallTab] = useState("desktop");

  const TABS = [
    { id:"apercu",    label:"Vue d'ensemble" },
    { id:"architecture", label:"Architecture" },
    { id:"branding",  label:"Branding" },
    { id:"code",      label:"Code clé" },
    { id:"install",   label:"Installation" },
    { id:"securite",  label:"Sécurité" },
  ];

  return (
    <div style={{ background:C.fond, minHeight:"100vh", color:C.texte,
      fontFamily:"'Segoe UI',Arial,sans-serif", padding:"0 0 40px" }}>

      {/* ── Header ─────────────────────────────────────────── */}
      <div style={{ background:`linear-gradient(135deg,${C.bleuF} 0%,${C.bleu} 60%,#1A3A5C 100%)`,
        padding:"32px 28px 24px", borderBottom:`2px solid ${C.or}44` }}>
        <div style={{ maxWidth:1100, margin:"0 auto" }}>
          <div style={{ display:"flex", alignItems:"center", gap:16, marginBottom:14 }}>
            <div dangerouslySetInnerHTML={{ __html:LOGO_SVG }}
              style={{ width:52, height:52 }} />
            <div>
              <h1 style={{ margin:0, fontSize:28, fontWeight:900, letterSpacing:-1,
                background:`linear-gradient(90deg,#fff,${C.orC})`,
                WebkitBackgroundClip:"text", WebkitTextFillColor:"transparent" }}>
                AkibaCore
              </h1>
              <p style={{ margin:0, color:C.orC, fontSize:13, fontStyle:"italic", opacity:.9 }}>
                Akiba ni nguvu ya kesho — L'épargne est la force de demain
              </p>
            </div>
            <div style={{ marginLeft:"auto", display:"flex", gap:8, flexWrap:"wrap" }}>
              <Badge color="#64B5F6">v2.0.0</Badge>
              <Badge color={C.vert}>100% Offline</Badge>
              <Badge color={C.or}>Desktop + Mobile</Badge>
              <Badge color={C.vertC}>Production Ready</Badge>
            </div>
          </div>

          {/* ── Tabs ─────────────────────────────────────────── */}
          <div style={{ display:"flex", gap:4, flexWrap:"wrap", marginTop:8 }}>
            {TABS.map(t => (
              <button key={t.id} onClick={() => setTab(t.id)} style={{
                padding:"8px 16px", borderRadius:8, border:"none", cursor:"pointer",
                fontSize:12.5, fontWeight:700, transition:"all .15s",
                background: tab===t.id ? C.or : "rgba(255,255,255,.07)",
                color: tab===t.id ? C.bleuF : C.sub,
              }}>{t.label}</button>
            ))}
          </div>
        </div>
      </div>

      <div style={{ maxWidth:1100, margin:"0 auto", padding:"24px 16px" }}>

        {/* ════════════ VUE D'ENSEMBLE ════════════ */}
        {tab === "apercu" && (
          <div>
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(200px,1fr))", gap:14, marginBottom:22 }}>
              {[
                { icon:"🖥️", label:"Desktop Windows", sub:"Electron + .exe", c:"#1E88E5" },
                { icon:"📱", label:"Mobile Android", sub:"React Native APK", c:"#43A047" },
                { icon:"🔄", label:"Synchronisation", sub:"Wi-Fi + USB", c:C.or },
                { icon:"🗃️", label:"SQLite local", sub:"WAL + FK + UUIDs", c:"#7E57C2" },
                { icon:"🔐", label:"Sécurisé", sub:"bcrypt + session", c:"#E53935" },
                { icon:"📊", label:"Audit log", sub:"Toutes les actions", c:"#00ACC1" },
              ].map(k => (
                <div key={k.label} style={{
                  background: C.card, border:`1px solid ${C.border}`,
                  borderRadius:12, padding:"18px 16px", textAlign:"center",
                  borderTop:`3px solid ${k.c}`,
                }}>
                  <div style={{ fontSize:28, marginBottom:8 }}>{k.icon}</div>
                  <div style={{ color:C.texte, fontWeight:700, fontSize:13 }}>{k.label}</div>
                  <div style={{ color:C.sub, fontSize:11, marginTop:4 }}>{k.sub}</div>
                </div>
              ))}
            </div>

            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
              <Card>
                <h3 style={{ color:C.or, marginTop:0, fontSize:15 }}>Fonctionnalités</h3>
                {[
                  "Gestion des membres (CRUD complet)",
                  "Dépôts d'épargne (3 types)",
                  "Octroi et suivi des crédits",
                  "Remboursements avec imputation automatique",
                  "Gestion des sessions/réunions AVEC",
                  "Tableau de bord avec KPIs temps réel",
                  "Journal d'audit complet",
                  "Export CSV + rapport HTML",
                  "Sauvegarde automatique (30 min)",
                  "Synchronisation Desktop ↔ Mobile",
                ].map(f => (
                  <div key={f} style={{ display:"flex", gap:8, alignItems:"center",
                    padding:"4px 0", fontSize:13, borderBottom:`1px solid ${C.border}44` }}>
                    <span style={{ color:C.vert, fontSize:11 }}>✓</span>
                    <span style={{ color:C.texte }}>{f}</span>
                  </div>
                ))}
              </Card>

              <Card>
                <h3 style={{ color:C.or, marginTop:0, fontSize:15 }}>Stack technique</h3>
                <table style={{ width:"100%", borderCollapse:"collapse", fontSize:12 }}>
                  <thead>
                    <tr style={{ borderBottom:`1px solid ${C.border}` }}>
                      {["Couche","Tech","Justification"].map(h => (
                        <th key={h} style={{ padding:"6px 8px", textAlign:"left", color:C.sub }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      ["Main Process","Node.js 18+","Runtime Electron"],
                      ["API interne","Express 4","REST local"],
                      ["Base de données","SQLite (better-sqlite3)","Synchrone, WAL, robuste"],
                      ["Desktop UI","Electron 30","Natif Windows"],
                      ["Mobile","React Native 0.73","APK Android"],
                      ["Sécurité","bcrypt + Helmet","Standards industrie"],
                      ["Logs","Winston","Fichiers rotatifs"],
                      ["Sync","Express + JSON","Wi-Fi local, USB"],
                    ].map(([a,b,c],i) => (
                      <tr key={i} style={{ background:i%2===0?"rgba(255,255,255,.02)":"transparent" }}>
                        <td style={{ padding:"5px 8px", color:C.or, fontSize:11 }}>{a}</td>
                        <td style={{ padding:"5px 8px", color:C.texte, fontFamily:"monospace", fontSize:11 }}>{b}</td>
                        <td style={{ padding:"5px 8px", color:C.sub, fontSize:11 }}>{c}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <h3 style={{ color:C.or, marginTop:18, fontSize:15 }}>Pourquoi React Native pour mobile ?</h3>
                <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
                  {[
                    ["✓","Même langage JS que le desktop (cohérence)"],
                    ["✓","SQLite disponible et stable (react-native-sqlite-storage)"],
                    ["✓","Génère un vrai APK Android signable"],
                    ["✓","Communauté large, docs abondantes"],
                    ["✓","Partage possible du code finance.js"],
                  ].map(([i,t]) => (
                    <div key={t} style={{ display:"flex", gap:8, fontSize:12, color:C.texte }}>
                      <span style={{ color:C.vert }}>{i}</span>{t}
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>
        )}

        {/* ════════════ ARCHITECTURE ════════════ */}
        {tab === "architecture" && (
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
            <Card>
              <h3 style={{ color:C.or, marginTop:0, fontSize:15 }}>Structure du projet</h3>
              <div style={{ background:"#070D14", borderRadius:8, padding:14 }}>
                <FileTree data={STRUCTURE} />
              </div>
            </Card>

            <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
              <Card>
                <h3 style={{ color:C.or, marginTop:0, fontSize:15 }}>Flux Desktop</h3>
                <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                  {[
                    { from:"Electron Main", to:"Express interne", note:"même process, port 49152" },
                    { from:"Express", to:"SQLite", note:"better-sqlite3 synchrone" },
                    { from:"BrowserWindow", to:"Renderer SPA", note:"localhost:49152" },
                    { from:"Renderer", to:"preload.js", note:"contextBridge sécurisé" },
                    { from:"preload.js", to:"IPC Main", note:"ipcRenderer.invoke()" },
                  ].map((f,i) => (
                    <div key={i} style={{ display:"flex", alignItems:"center", gap:8, fontSize:12 }}>
                      <span style={{ color:C.texte, fontFamily:"monospace", fontSize:11,
                        background:"rgba(255,255,255,.05)", padding:"2px 8px", borderRadius:4, minWidth:130 }}>{f.from}</span>
                      <span style={{ color:C.or }}>→</span>
                      <span style={{ color:C.orC, fontFamily:"monospace", fontSize:11,
                        background:"rgba(201,168,76,.08)", padding:"2px 8px", borderRadius:4, minWidth:130 }}>{f.to}</span>
                      <span style={{ color:C.sub, fontSize:10 }}>{f.note}</span>
                    </div>
                  ))}
                </div>
              </Card>

              <Card>
                <h3 style={{ color:C.or, marginTop:0, fontSize:15 }}>Flux Synchronisation</h3>
                {[
                  { mode:"Wi-Fi local", steps:[
                    "Desktop → démarre sync-server.js (port 7777)",
                    "Mobile → rejoint le même réseau Wi-Fi",
                    "Mobile → GET /sync/export?since=XXXX",
                    "Mobile → intègre les données desktop",
                    "Mobile → POST /sync/import (données non sync)",
                    "Résolution : LAST-WRITE-WINS (date modifie_le)",
                    "UUIDs → identité cross-device garantie",
                  ]},
                  { mode:"USB / JSON", steps:[
                    "Desktop → node usb-export.js export D:\\",
                    "Fichier JSON → clé USB → autre PC",
                    "Desktop → node usb-export.js import D:\\XXX.json",
                    "INSERT OR IGNORE → pas de doublons",
                  ]},
                ].map(m => (
                  <div key={m.mode} style={{ marginBottom:14 }}>
                    <div style={{ color:C.texte, fontWeight:700, fontSize:12, marginBottom:6 }}>
                      <Badge color={C.bleu}>{m.mode}</Badge>
                    </div>
                    {m.steps.map((s,i) => (
                      <div key={i} style={{ display:"flex", gap:8, fontSize:11, color:C.sub,
                        padding:"2px 0", borderLeft:`2px solid ${C.border}`, paddingLeft:8, marginBottom:2 }}>
                        <span style={{ color:C.or }}>{i+1}.</span>{s}
                      </div>
                    ))}
                  </div>
                ))}
              </Card>

              <Card>
                <h3 style={{ color:C.or, marginTop:0, fontSize:15 }}>Schéma SQLite</h3>
                <div style={{ display:"flex", flexWrap:"wrap", gap:8 }}>
                  {[
                    { t:"utilisateurs", c:["id","nom","login","pwd_hash","role"] },
                    { t:"membres", c:["id","uuid","nom","prenom","telephone","statut","synced"] },
                    { t:"epargnes", c:["id","uuid","membre_id","montant","type","annule"] },
                    { t:"credits", c:["id","uuid","membre_id","principal","taux","statut"] },
                    { t:"remboursements", c:["id","uuid","credit_id","mont_total"] },
                    { t:"audit_log", c:["id","login","action","tbl","ts"] },
                    { t:"sync_log", c:["id","direction","source","nb_records"] },
                  ].map(tb => (
                    <div key={tb.t} style={{ background:"#070D14", border:`1px solid ${C.border}`,
                      borderRadius:8, padding:"10px 14px", minWidth:160 }}>
                      <div style={{ color:C.or, fontFamily:"monospace", fontSize:12,
                        fontWeight:700, marginBottom:6, borderBottom:`1px solid ${C.border}`, paddingBottom:4 }}>
                        {tb.t}
                      </div>
                      {tb.c.map(col => (
                        <div key={col} style={{ color:C.sub, fontSize:10, fontFamily:"monospace",
                          padding:"1px 0" }}>
                          • {col}
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>
        )}

        {/* ════════════ BRANDING ════════════ */}
        {tab === "branding" && (
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
            <Card>
              <h3 style={{ color:C.or, marginTop:0 }}>Logo & Identité</h3>
              <div style={{ display:"flex", gap:16, alignItems:"center", marginBottom:20 }}>
                <div dangerouslySetInnerHTML={{ __html:LOGO_SVG }}
                  style={{ width:80, height:80 }} />
                <div>
                  <div style={{ fontSize:24, fontWeight:900, color:C.or, letterSpacing:-1 }}>AkibaCore</div>
                  <div style={{ color:C.sub, fontSize:12, marginTop:4 }}>
                    <em>"Akiba ni nguvu ya kesho"</em><br/>
                    L'épargne est la force de demain (Swahili)
                  </div>
                </div>
              </div>

              <h4 style={{ color:C.texte, fontSize:13 }}>Code SVG du logo</h4>
              <CodeBlock lang="svg" code={`<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#1A3A5C"/>
      <stop offset="100%" stop-color="#0F2237"/>
    </linearGradient>
  </defs>
  <!-- Fond bleu profond arrondi -->
  <rect width="80" height="80" rx="18" fill="url(#g)"/>
  <!-- Lettre A — pilier de l'AVEC -->
  <text x="40" y="55" font-family="Arial Black" font-size="46"
        fill="#C9A84C" text-anchor="middle" font-weight="900">A</text>
  <!-- Barre dorée — solidarité -->
  <rect x="14" y="62" width="52" height="4" rx="2"
        fill="#C9A84C" opacity="0.5"/>
</svg>`} />

              <h4 style={{ color:C.texte, fontSize:13, marginTop:16 }}>Typographie</h4>
              {[
                { name:"Titres / Logo", font:"Arial Black / Segoe UI Black", weight:"900" },
                { name:"Corps de texte", font:"Segoe UI / Arial",             weight:"400–600" },
                { name:"Code / Données", font:"Courier New / JetBrains Mono", weight:"400" },
              ].map(t => (
                <div key={t.name} style={{ display:"flex", justifyContent:"space-between",
                  padding:"7px 0", borderBottom:`1px solid ${C.border}`, fontSize:12 }}>
                  <span style={{ color:C.sub }}>{t.name}</span>
                  <span style={{ color:C.texte, fontFamily:"monospace" }}>{t.font}</span>
                  <span style={{ color:C.or }}>{t.weight}</span>
                </div>
              ))}
            </Card>

            <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
              <Card>
                <h3 style={{ color:C.or, marginTop:0 }}>Palette de couleurs</h3>
                <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                  {PALETTE.map(p => (
                    <div key={p.hex} style={{ display:"flex", alignItems:"center", gap:12 }}>
                      <div style={{ width:36, height:36, borderRadius:8,
                        background:p.hex, border:`1px solid rgba(255,255,255,.1)`,
                        flexShrink:0 }} />
                      <div style={{ flex:1 }}>
                        <div style={{ color:C.texte, fontSize:13, fontWeight:600 }}>{p.name}</div>
                        <div style={{ color:C.sub, fontSize:11 }}>{p.role}</div>
                      </div>
                      <code style={{ color:C.or, fontSize:11, fontFamily:"monospace" }}>{p.hex}</code>
                    </div>
                  ))}
                </div>
              </Card>

              <Card>
                <h3 style={{ color:C.or, marginTop:0 }}>Aperçu écrans</h3>
                {/* Mini aperçu du dashboard */}
                <div style={{ background:"#070D14", borderRadius:10, padding:14,
                  border:`1px solid ${C.border}` }}>
                  <div style={{ fontSize:11, color:C.or, fontWeight:700, marginBottom:8 }}>
                    Tableau de bord — AkibaCore Desktop
                  </div>
                  <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:6, marginBottom:10 }}>
                    {[
                      { v:"128", l:"Membres",    bg:"#1A3A5C" },
                      { v:"2.4M FC",l:"Épargnes", bg:"#1A6B45" },
                      { v:"850K FC",l:"Crédits",  bg:"#7D6808" },
                      { v:"0",     l:"Retards",   bg:"#1A3A5C" },
                      { v:"12",    l:"Sessions",  bg:"#6C3483" },
                      { v:"1.5M",  l:"Solde net", bg:"#1A6B45" },
                    ].map(k => (
                      <div key={k.l} style={{ background:k.bg, borderRadius:6,
                        padding:"6px 8px", textAlign:"center" }}>
                        <div style={{ color:"#fff", fontWeight:900, fontSize:11 }}>{k.v}</div>
                        <div style={{ color:"rgba(255,255,255,.7)", fontSize:9 }}>{k.l}</div>
                      </div>
                    ))}
                  </div>
                  <div style={{ background:"#0A0F1A", borderRadius:6, padding:8 }}>
                    <div style={{ display:"grid", gridTemplateColumns:"2fr 1fr 1fr 1fr",
                      gap:4, fontSize:9, color:C.sub, marginBottom:4 }}>
                      {["Membre","Principal","Solde","Statut"].map(h=>
                        <span key={h} style={{ fontWeight:700 }}>{h}</span>)}
                    </div>
                    {[
                      ["Amani Bahati","500 000 FC","420 000 FC","ACTIF"],
                      ["Déborah Muila","300 000 FC","0 FC","SOLDÉ"],
                      ["Théo Kambale","800 000 FC","800 000 FC","RETARD"],
                    ].map(([n,p,s,st]) => (
                      <div key={n} style={{ display:"grid", gridTemplateColumns:"2fr 1fr 1fr 1fr",
                        gap:4, fontSize:9, color:C.texte, padding:"3px 0",
                        borderBottom:`1px solid ${C.border}44` }}>
                        <span>{n}</span><span>{p}</span><span>{s}</span>
                        <span style={{ color:st==="RETARD"?C.rouge:st==="SOLDÉ"?C.vert:C.or }}>{st}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>

              <Card>
                <h3 style={{ color:C.or, marginTop:0 }}>Slogans proposés</h3>
                {[
                  { sl:"Akiba ni nguvu ya kesho", note:"Swahili — Slogan principal" },
                  { sl:"Votre épargne. Votre force.", note:"Français — Usage terrain" },
                  { sl:"Finance locale. Pouvoir communautaire.", note:"Français — Institucional" },
                  { sl:"La donnée au service du village.", note:"Français — Tech-focused" },
                ].map(s => (
                  <div key={s.sl} style={{ padding:"8px 0", borderBottom:`1px solid ${C.border}` }}>
                    <div style={{ color:C.or, fontStyle:"italic", fontSize:13 }}>"{s.sl}"</div>
                    <div style={{ color:C.sub, fontSize:11, marginTop:2 }}>{s.note}</div>
                  </div>
                ))}
              </Card>
            </div>
          </div>
        )}

        {/* ════════════ CODE CLÉ ════════════ */}
        {tab === "code" && (
          <div>
            <div style={{ display:"flex", gap:6, marginBottom:16, flexWrap:"wrap" }}>
              {[
                { id:"finance",      label:"Finance (calculs)" },
                { id:"sync",         label:"Synchronisation" },
                { id:"mobile_db",    label:"DB Mobile (RN)" },
                { id:"electron_main",label:"Main Electron" },
                { id:"schema_sql",   label:"Schéma SQL" },
              ].map(t => (
                <button key={t.id} onClick={() => setCodeTab(t.id)} style={{
                  padding:"7px 14px", borderRadius:8, border:"none", cursor:"pointer",
                  fontSize:12, fontWeight:700,
                  background: codeTab===t.id ? C.or : C.card,
                  color:      codeTab===t.id ? C.bleuF : C.sub,
                  border:     `1px solid ${codeTab===t.id ? C.or : C.border}`,
                }}>{t.label}</button>
              ))}
            </div>
            <CodeBlock lang={codeTab === "schema_sql" ? "sql" : "javascript"}
              code={CODE_SAMPLES[codeTab]} />

            <div style={{ marginTop:16, display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
              <Card>
                <h4 style={{ color:C.or, marginTop:0, fontSize:13 }}>Sécurité preload.js</h4>
                <CodeBlock lang="javascript" code={`// Pont sécurisé Renderer ↔ Main
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('akiba', {
  // Seules ces fonctions sont exposées
  getVersion:    () => ipcRenderer.invoke('get-app-version'),
  triggerBackup: () => ipcRenderer.invoke('trigger-backup'),
  showConfirm: (t, m) =>
    ipcRenderer.invoke('show-confirm', { title:t, message:m }),
  onAction: (cb) =>
    ipcRenderer.on('action', (_, data) => cb(data)),

  isElectron: true,
  platform: process.platform,
  // Node.js jamais exposé directement
});`} />
              </Card>

              <Card>
                <h4 style={{ color:C.or, marginTop:0, fontSize:13 }}>Transaction atomique</h4>
                <CodeBlock lang="javascript" code={`// Remboursement en transaction atomique
const txn = db.transaction(() => {
  // 1. Enregistrer le remboursement
  const rid = db.prepare(\`
    INSERT INTO remboursements(
      credit_id, montant_total, ...
    ) VALUES(?,?,...)
  \`).run(credit_id, mt, ...).lastInsertRowid;

  // 2. Mettre à jour le solde crédit
  db.prepare(\`
    UPDATE credits SET rembourse=?, statut=?
    WHERE id=?
  \`).run(nouveauRembourse, nouveauStatut, credit_id);

  return rid;
});

// Si une opération échoue → tout est annulé
const remb_id = txn();`} />
              </Card>
            </div>
          </div>
        )}

        {/* ════════════ INSTALLATION ════════════ */}
        {tab === "install" && (
          <div>
            <div style={{ display:"flex", gap:6, marginBottom:16, flexWrap:"wrap" }}>
              {[
                { id:"desktop",   label:"🖥️ Desktop Windows" },
                { id:"android",   label:"📱 APK Android" },
                { id:"sync_wifi", label:"📡 Sync Wi-Fi" },
                { id:"sync_usb",  label:"💾 Sync USB" },
              ].map(t => (
                <button key={t.id} onClick={() => setInstallTab(t.id)} style={{
                  padding:"8px 16px", borderRadius:8, border:"none", cursor:"pointer",
                  fontSize:12.5, fontWeight:700,
                  background: installTab===t.id ? C.or : C.card,
                  color:      installTab===t.id ? C.bleuF : C.sub,
                  border:     `1px solid ${installTab===t.id ? C.or : C.border}`,
                }}>{t.label}</button>
              ))}
            </div>

            <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
              {INSTALL_STEPS[installTab].map((s, i) => (
                <div key={i} style={{
                  display:"flex", gap:14, alignItems:"flex-start",
                  background: C.card, border:`1px solid ${C.border}`,
                  borderRadius:10, padding:"14px 18px",
                  borderLeft:`3px solid ${C.or}`,
                }}>
                  <div style={{
                    background: C.or, color: C.bleuF,
                    borderRadius:"50%", width:26, height:26,
                    display:"flex", alignItems:"center", justifyContent:"center",
                    fontWeight:900, fontSize:13, flexShrink:0,
                  }}>{s.n}</div>
                  <div style={{ flex:1 }}>
                    <div style={{ color:C.sub, fontSize:11, marginBottom:6 }}>{s.desc}</div>
                    <code style={{
                      display:"block", background:"#070D14",
                      border:`1px solid ${C.border}`, borderRadius:6,
                      padding:"8px 12px", fontSize:11.5, color:"#86BFFF",
                      fontFamily:"'Courier New',monospace", wordBreak:"break-all",
                    }}>{s.cmd}</code>
                  </div>
                </div>
              ))}
            </div>

            {installTab === "desktop" && (
              <Card style={{ marginTop:16 }}>
                <h4 style={{ color:C.or, marginTop:0 }}>Prérequis Windows</h4>
                <div style={{ display:"flex", flexWrap:"wrap", gap:10 }}>
                  {[
                    { tool:"Node.js", ver:"≥ 18.x", url:"nodejs.org" },
                    { tool:"Git",     ver:"≥ 2.x",  url:"git-scm.com" },
                    { tool:"Windows", ver:"10/11",   url:"—" },
                    { tool:"RAM",     ver:"≥ 2 GB",  url:"—" },
                    { tool:"Disque",  ver:"≥ 200 MB",url:"—" },
                  ].map(p => (
                    <div key={p.tool} style={{ background:"#070D14",
                      border:`1px solid ${C.border}`, borderRadius:8,
                      padding:"8px 14px", minWidth:110, textAlign:"center" }}>
                      <div style={{ color:C.texte, fontSize:12, fontWeight:700 }}>{p.tool}</div>
                      <div style={{ color:C.or, fontSize:11 }}>{p.ver}</div>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {installTab === "android" && (
              <Card style={{ marginTop:16 }}>
                <h4 style={{ color:C.or, marginTop:0 }}>Configuration Android Studio</h4>
                <CodeBlock lang="bash" code={`# Variables d'environnement Windows
# → Panneau de configuration → Variables d'environnement

ANDROID_HOME = C:\\Users\\<user>\\AppData\\Local\\Android\\Sdk
JAVA_HOME    = C:\\Program Files\\Android Studio\\jbr

# Ajouter au PATH :
%ANDROID_HOME%\\platform-tools
%ANDROID_HOME%\\tools

# Vérifier :
adb --version
java --version  # doit être >= 17`} />
              </Card>
            )}
          </div>
        )}

        {/* ════════════ SÉCURITÉ ════════════ */}
        {tab === "securite" && (
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
            <Card>
              <h3 style={{ color:C.or, marginTop:0 }}>Mesures de sécurité</h3>
              {[
                { cat:"Authentification", items:[
                  "Mots de passe hachés bcrypt (coût 12)",
                  "Sessions serveur uniquement (httpOnly, sameSite:strict)",
                  "Durée session : 8 heures maximum",
                  "Aucun token côté client",
                ]},
                { cat:"Architecture Electron", items:[
                  "nodeIntegration: false (renderer isolé)",
                  "contextIsolation: true (pas d'accès Node)",
                  "preload.js = seul pont autorisé",
                  "Serveur sur 127.0.0.1 uniquement",
                  "webSecurity: true activé",
                ]},
                { cat:"HTTP / Express", items:[
                  "Helmet.js (X-Frame-Options, CSP, etc.)",
                  "Content-Security-Policy stricte",
                  "CORS désactivé (localhost only)",
                  "JSON body limit : 2 MB",
                ]},
                { cat:"Base de données", items:[
                  "Clés étrangères activées (PRAGMA foreign_keys=ON)",
                  "WAL mode (résistance aux coupures)",
                  "Contraintes CHECK sur toutes les tables",
                  "Transactions atomiques pour opérations critiques",
                ]},
                { cat:"Données", items:[
                  "Audit log de toutes les actions",
                  "Sauvegarde automatique toutes les 30 min",
                  "Rotation des sauvegardes (max 20 fichiers)",
                  "Stockage dans AppData (isolé par utilisateur Windows)",
                ]},
                { cat:"Synchronisation", items:[
                  "Clé partagée (x-sync-key header)",
                  "Serveur sync = réseau local uniquement",
                  "Validation de toutes les données importées",
                  "INSERT OR IGNORE (pas de doublons)",
                ]},
              ].map(s => (
                <div key={s.cat} style={{ marginBottom:14 }}>
                  <div style={{ color:C.texte, fontWeight:700, fontSize:12,
                    marginBottom:6, display:"flex", gap:6, alignItems:"center" }}>
                    <span style={{ color:C.vert }}>■</span>{s.cat}
                  </div>
                  {s.items.map(item => (
                    <div key={item} style={{ display:"flex", gap:8, fontSize:11,
                      color:C.sub, padding:"2px 0", paddingLeft:12 }}>
                      <span style={{ color:C.vert, fontSize:10 }}>✓</span>{item}
                    </div>
                  ))}
                </div>
              ))}
            </Card>

            <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
              <Card>
                <h3 style={{ color:C.or, marginTop:0 }}>Audit Log</h3>
                <CodeBlock lang="sql" code={`-- Chaque action est enregistrée
SELECT ts, login, action, tbl, details
FROM audit_log ORDER BY id DESC LIMIT 10;

-- Exemples d'actions tracées :
-- CONNEXION, DÉCONNEXION
-- AJOUTER_MEMBRE, MODIFIER_MEMBRE
-- AJOUTER_EPARGNE, ANNULER_EPARGNE
-- OCTROYER_CREDIT
-- REMBOURSEMENT
-- SAUVEGARDE, EXPORT_CSV
-- CREER_SESSION, CLOTURER_SESSION`} />
              </Card>

              <Card>
                <h3 style={{ color:C.or, marginTop:0 }}>Sauvegarde automatique</h3>
                <CodeBlock lang="javascript" code={`// Déclenché toutes les 30 minutes
// ET au démarrage, ET à la fermeture

function sauvegarder() {
  const base = app.getPath('userData');
  const ts   = new Date().toISOString()
    .replace(/[:.]/g, '-').slice(0, 19);
  const dest = path.join(base, 'sauvegardes',
    \`akibacore_\${ts}.db\`);

  // Copie atomique du fichier SQLite
  fs.copyFileSync(
    path.join(base, 'data', 'akibacore.db'),
    dest
  );

  // Purge automatique (max 20 sauvegardes)
  const files = fs.readdirSync(dir)
    .filter(f => f.endsWith('.db')).sort();
  while (files.length > 20)
    fs.unlinkSync(path.join(dir, files.shift()));
}

// Emplacement Windows :
// C:\\Users\\<user>\\AppData\\Roaming\\AkibaCore\\sauvegardes\\`} />
              </Card>

              <Card>
                <h3 style={{ color:C.or, marginTop:0 }}>Validation des entrées</h3>
                <CodeBlock lang="javascript" code={`// Toutes les données validées côté serveur
// Jamais côté client uniquement

router.post('/credits', reqAuth, (req, res) => {
  const p = parseFloat(principal);
  const t = parseFloat(taux);

  if (!membre_id)
    return res.status(400).json({ message:'Membre requis.' });
  if (isNaN(p) || p <= 0)
    return res.status(400).json({ message:'Principal invalide.' });
  if (isNaN(t) || t <= 0 || t > 1)
    return res.status(400).json({ message:'Taux: 0 < t ≤ 1' });

  // SQLite ALSO checks: CHECK(principal > 0)
  // Double protection : code + contrainte DB
});`} />
              </Card>
            </div>
          </div>
        )}
      </div>

      {/* ── Footer ─────────────────────────────────────────── */}
      <div style={{ maxWidth:1100, margin:"24px auto 0", padding:"0 16px" }}>
        <div style={{ background:C.card, border:`1px solid ${C.border}`,
          borderRadius:12, padding:"16px 22px", display:"flex",
          justifyContent:"space-between", alignItems:"center", flexWrap:"wrap", gap:12 }}>
          <div style={{ display:"flex", alignItems:"center", gap:12 }}>
            <div dangerouslySetInnerHTML={{ __html:LOGO_SVG }} style={{ width:32, height:32 }} />
            <div>
              <span style={{ color:C.or, fontWeight:800, fontSize:14 }}>AkibaCore v2.0</span>
              <span style={{ color:C.sub, fontSize:11, marginLeft:10 }}>
                Desktop + Mobile + Sync — 100% Offline
              </span>
            </div>
          </div>
          <div style={{ display:"flex", gap:8 }}>
            <Badge color={C.vert}>Prêt pour production</Badge>
            <Badge color={C.or}>Optimisé machines légères</Badge>
          </div>
        </div>
      </div>
    </div>
  );
}
