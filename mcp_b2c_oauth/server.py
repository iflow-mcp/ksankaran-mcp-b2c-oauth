"""Simple MCP Server with Google OAuth Authentication."""
from dotenv import load_dotenv

load_dotenv()

import logging
import jwt
import httpx
import os
from typing import Any, Literal, Optional

import click
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from mcp.server.fastmcp.server import FastMCP
from .auth.google_oauth_provider import GoogleOAuthProvider
from .utils.server_settings import ServerSettings

logger = logging.getLogger(__name__)

def create_simple_mcp_server(settings: Optional[ServerSettings] = None, disable_auth: bool = False) -> FastMCP:
    """Create a simple FastMCP server with ADP OAuth."""
    
    if disable_auth:
        # 创建不带 OAuth 的服务器用于本地测试
        app = FastMCP(
            name="Google MCP Server",
            instructions="MCP server with Google OAuth Implementation",
            debug=True,
        )
        
        @app.tool(description="Get the authenticated user's Google profile information")
        async def get_google_profile() -> dict[str, Any]:
            """Get the authenticated user's profile information.

            This is the only tool in our example.
            """
            # 返回模拟数据用于本地测试
            return {
                "id": "test_user_id",
                "email": "test@example.com",
                "verified_email": True,
                "name": "Test User",
                "given_name": "Test",
                "family_name": "User",
                "picture": "https://example.com/picture.jpg",
                "locale": "en"
            }
    else:
        oauth_provider = GoogleOAuthProvider(settings)

        auth_settings = AuthSettings(
            issuer_url=settings.server_url,
            client_registration_options=ClientRegistrationOptions(
                enabled=True,
                valid_scopes=settings.scope.split(),
                default_scopes=settings.scope.split(),
            ),
            required_scopes=["openid"],
        )

        app = FastMCP(
            name="Google MCP Server",
            instructions="MCP server with Google OAuth Implementation",
            auth_server_provider=oauth_provider,
            host=settings.host,
            port=settings.port,
            debug=True,
            auth=auth_settings,
        )

        @app.custom_route("/callback", methods=["GET"])
        async def callback_handler(request: Request) -> Response:
            """Handle Google OAuth callback."""
            code = request.query_params.get("code")
            state = request.query_params.get("state")

            if not code or not state:
                raise HTTPException(400, "Missing code or state parameter")

            try:
                redirect_uri = await oauth_provider.handle_callback(code, state)
                return RedirectResponse(status_code=302, url=redirect_uri)
            except HTTPException:
                raise
            except Exception as e:
                logger.error("Unexpected error", exc_info=e)
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "server_error",
                        "error_description": "Unexpected error",
                    },
                )

        def get_token() -> str:
            """Get the ADP token for the authenticated user."""
            access_token = get_access_token()
            if not access_token:
                raise ValueError("Not authenticated")

            # Get ADP token from mapping
            adp_token = oauth_provider.token_mapping.get(access_token.token)

            if not adp_token:
                raise ValueError("No ADP token found for user")

            return adp_token

        @app.tool(description="Get the authenticated user's Google profile information")
        async def get_google_profile() -> dict[str, Any]:
            """Get the authenticated user's profile information.

            This is the only tool in our example.
            """
            google_token = get_token()
            
            # make a request to Google API to get user profile using httpx
            user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    user_info_url,
                    headers={"Authorization": f"Bearer {google_token}"}
                )
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Failed to fetch user profile"
                    )
                return response.json()

    return app


@click.command()
@click.option("--port", default=3000, help="Port to listen on")
@click.option("--host", default="localhost", help="Host to bind to")
@click.option(
    "--transport",
    default="streamable-http",
    type=click.Choice(["sse", "streamable-http", "stdio"]),
    help="Transport protocol to use ('sse', 'streamable-http', or 'stdio')",
)
@click.option("--disable-auth", is_flag=True, help="Disable OAuth authentication for local testing")
def main(port: int, host: str, transport: Literal["sse", "streamable-http", "stdio"], disable_auth: bool) -> int:
    """Run the simple Google MCP server."""
    logging.basicConfig(level=logging.INFO)

    # 检查是否为 stdio 协议
    if transport == "stdio":
        disable_auth = True  # stdio 协议不需要 OAuth
    
    settings = None
    if not disable_auth:
        try:
            # No hardcoded credentials - all from environment variables
            settings = ServerSettings(host=host, port=port)
        except ValueError as e:
            logger.error("Failed to load settings. Make sure environment variables are set:")
            logger.error("  MCP_CLIENT_ID=<your-client-id>")
            logger.error("  MCP_CLIENT_SECRET=<your-client-secret>")
            logger.error(f"Error: {e}")
            return 1
    else:
        # 创建一个最小化的 settings 对象用于本地测试
        # 注意：在 disable_auth 模式下，我们不需要真实的 settings
        pass

    mcp_server = create_simple_mcp_server(settings, disable_auth=disable_auth)
    logger.info(f"Starting server with {transport} transport (auth={'disabled' if disable_auth else 'enabled'})")
    mcp_server.run(transport=transport)
    return 0