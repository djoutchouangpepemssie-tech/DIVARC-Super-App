import { NextResponse } from 'next/server'

// Filtre anti-bruit : notre app n'utilise AUCUNE "Server Action" Next.js. Les requêtes
// portant l'en-tête `next-action` sont donc forcément illégitimes (scanners / vieux clients
// en cache). On les rejette proprement AVANT que Next ne tente de les traiter — ce qui évite
// les logs répétés « Failed to find Server Action ». N'affecte ni les pages, ni le proxy /api.
export function middleware(request) {
  if (request.headers.get('next-action')) {
    return new NextResponse(null, { status: 404 })
  }
  return NextResponse.next()
}

// Ne s'exécute pas sur les assets statiques (perf).
export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
