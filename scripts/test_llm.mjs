import { LlmChat, UserMessage } from 'emergentintegrations'
import fs from 'fs'

const env = fs.readFileSync('/app/.env', 'utf8')
const key = (env.match(/^EMERGENT_LLM_KEY=(.*)$/m) || [])[1]

const SYSTEM = `Tu es DIVA, le copilote IA de DIVARC. Réponds en français, court. Retourne UNIQUEMENT du JSON valide (sans markdown) au format {"assistant_message": string, "actions": []}.`

async function main() {
  const chat = new LlmChat(key, 'test-session-1', SYSTEM)
    .withModel('anthropic', 'claude-sonnet-4-5-20250929')
    .withParams({ max_tokens: 500 })
  const reply = await chat.sendMessage(new UserMessage({ text: 'Bonjour, qui es-tu ?' }))
  console.log('REPLY:', reply)
}
main().catch((e) => { console.error('ERR:', e?.message || e); process.exit(1) })
