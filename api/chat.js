const ALLOWED_LOCALES = new Set(['es', 'en']);
const CARD_FIELDS = [
  'Card Name', 'Card Number', 'Arcana', 'Suit', 'Element', 'Core Theme',
  'Brief Description', 'Keywords Upright', 'Keywords Reversed', 'Affirmation',
  'Emotional Meaning', 'Career Meaning', 'Spiritual Layer', 'Psychological Shadow', 'Orientation'
];
const requestLog = new Map();

function cleanCard(card = {}) {
  return Object.fromEntries(CARD_FIELDS.map(key => [key, String(card[key] ?? '').slice(0, 700)]));
}

function rateLimited(req) {
  const key = String(req.headers['x-forwarded-for'] || req.socket?.remoteAddress || 'unknown').split(',')[0];
  const now = Date.now();
  const recent = (requestLog.get(key) || []).filter(time => now - time < 60000);
  recent.push(now);
  requestLog.set(key, recent);
  return recent.length > 15;
}

function readingPrompt(cards, locale, manual, focus) {
  const language = locale === 'es' ? 'español rioplatense natural' : 'natural English';
  const positions = manual ? cards.map((_, i) => locale==='es'?`Carta ${i + 1}`:`Card ${i + 1}`) : (locale==='es'?['Pasado', 'Presente', 'Futuro']:['Past','Present','Future']);
  const description = cards.map((card, index) => {
    const c = cleanCard(card);
    return `${positions[index] || `Card ${index + 1}`}: ${c['Card Name']} (${c.Orientation||'Upright'})\nTema: ${c['Core Theme']}\nSignificado emocional: ${c['Emotional Meaning']}\nCapa espiritual: ${c['Spiritual Layer']}\nSombra: ${c['Psychological Shadow']}`;
  }).join('\n\n');

  const intention=focus?`\nLa persona quiere explorar: "${focus}". Respondé a esa intención de forma concreta, sin repetirla literalmente.\n`:'';
  return `Sos la lectora de Solar Kingdom Tarot. Leé esta combinación como una historia única para la persona que acaba de sacar estas cartas:${intention}\n${description}\n\nEscribí solamente la lectura en ${language}. Respetá si cada carta está al derecho o invertida. Conectá las cartas entre sí: buscá tensiones, repeticiones y la evolución de una hacia otra. No enumeres significados ni repitas los nombres de todas las cartas. Evitá frases genéricas como "el universo te dice", "en este momento de tu vida" o "recordá que". Variá el ritmo de las frases y hablá con calidez, intuición y honestidad, como alguien perceptivo que conoce bien a quien consulta. No hagas predicciones absolutas ni menciones que sos una IA. Cerrá con una pregunta concreta que nazca de esta combinación. Sin títulos ni viñetas. Entre ${manual ? '80 y 120' : '120 y 170'} palabras.`;
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });
  if (rateLimited(req)) return res.status(429).json({ error: 'Too many requests' });
  if (!process.env.GEMINI_API_KEY) return res.status(503).json({ error: 'Gemini service unavailable' });

  const { action, locale = 'es' } = req.body || {};
  if (action !== 'reading') return res.status(400).json({ error: 'Invalid action' });
  if (!ALLOWED_LOCALES.has(locale)) return res.status(400).json({ error: 'Invalid locale' });
  const cards = Array.isArray(req.body.cards) ? req.body.cards.slice(0, 10) : [];
  const focus = String(req.body.focus || '').slice(0, 300);
  if (!cards.length) return res.status(400).json({ error: 'Cards are required' });

  try {
    const model = process.env.GEMINI_MODEL || 'gemini-2.5-flash-lite';
    const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(process.env.GEMINI_API_KEY)}`;
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ role: 'user', parts: [{ text: readingPrompt(cards, locale, Boolean(req.body.manual), focus) }] }],
        generationConfig: {
          temperature: 0.95,
          topP: 0.95,
          maxOutputTokens: 600,
          responseMimeType: 'text/plain'
        }
      })
    });
    const data = await response.json();
    if (!response.ok) {
      console.error('Gemini API error:', response.status, data?.error?.message || 'unknown');
      return res.status(response.status).json({ error: 'AI request failed' });
    }
    const text = (data?.candidates?.[0]?.content?.parts || []).map(part => part.text || '').join('').trim();
    if (!text) return res.status(502).json({ error: 'Empty AI response' });
    return res.status(200).json({ text });
  } catch (error) {
    console.error('Tarot API error:', error.message);
    return res.status(500).json({ error: 'Unable to complete request' });
  }
};
