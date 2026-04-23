import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Public routes that don't require authentication
const publicRoutes = ['/login', '/register'];

// Routes that should redirect to home if already authenticated
const authRoutes = ['/login', '/register'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Get refresh token from cookies (httpOnly cookie set by backend)
  const refreshToken = request.cookies.get('refresh_token')?.value;
  const hasRefreshToken = !!refreshToken;

  // Detect if request is behind a proxy (ngrok, reverse proxy, etc.)
  // When proxied, the refresh_token cookie is set on the backend's domain (e.g. localhost),
  // not the proxy domain (e.g. xxxx.ngrok.io), so middleware can't see it.
  // In this case, skip the redirect and let client-side AuthContext handle auth.
  const isProxied = !!(
    request.headers.get('x-forwarded-for') ||
    request.headers.get('x-forwarded-host') ||
    request.headers.get('x-forwarded-proto')
  );

  console.debug('[Middleware] Path:', pathname, 'Has refresh token:', hasRefreshToken, 'Proxied:', isProxied);

  // Check if the current path is public
  const isPublicRoute = publicRoutes.some((route) => pathname.startsWith(route));

  // Allow access to auth pages regardless of token presence
  // This prevents redirect loops when tokens are stale/expired
  // The AuthContext will handle actual validation and show errors if token is invalid
  const isAuthRoute = authRoutes.some((route) => pathname.startsWith(route));
  if (isAuthRoute) {
    console.debug('[Middleware] Auth page access allowed');
    return NextResponse.next();
  }

  // If behind a proxy, skip server-side redirect — client-side auth handles it
  if (isProxied) {
    console.debug('[Middleware] Proxied request, deferring auth check to client');
    return NextResponse.next();
  }

  // If user has no refresh token and trying to access protected route, redirect to login
  if (!hasRefreshToken && !isPublicRoute) {
    console.debug('[Middleware] No refresh token, redirecting to login');
    return NextResponse.redirect(new URL('/login', request.url));
  }

  return NextResponse.next();
}

// Configure which routes the middleware runs on
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - uploads (file uploads)
     * - api routes (handled by backend API, not Next.js middleware)
     */
    '/((?!_next/static|_next/image|favicon.ico|uploads|api).*)',
  ],
};
