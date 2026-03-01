"""Plaid API client wrapper using plaid-python SDK."""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_plaid_client():
    """Create and return a configured Plaid API client."""
    try:
        import plaid
        from plaid.api import plaid_api

        env_map = {
            'sandbox': plaid.Environment.Sandbox,
            'production': plaid.Environment.Production,
        }
        host = env_map.get(
            getattr(settings, 'PLAID_ENV', 'sandbox'),
            plaid.Environment.Sandbox,
        )

        configuration = plaid.Configuration(
            host=host,
            api_key={
                'clientId': getattr(settings, 'PLAID_CLIENT_ID', ''),
                'secret': getattr(settings, 'PLAID_SECRET', ''),
            }
        )
        api_client = plaid.ApiClient(configuration)
        return plaid_api.PlaidApi(api_client)
    except ImportError:
        logger.error("plaid-python package is not installed")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize Plaid client: {e}")
        raise


def create_link_token(client_user_id='default-user'):
    """Create a Plaid Link token for the frontend."""
    from plaid.model.link_token_create_request import LinkTokenCreateRequest
    from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
    from plaid.model.products import Products
    from plaid.model.country_code import CountryCode

    client = _get_plaid_client()
    request = LinkTokenCreateRequest(
        products=[Products('investments')],
        client_name='Financial Accounting',
        country_codes=[CountryCode('US')],
        language='en',
        user=LinkTokenCreateRequestUser(client_user_id=client_user_id),
    )
    response = client.link_token_create(request)
    return {
        'link_token': response.link_token,
        'expiration': response.expiration,
    }


def exchange_public_token(public_token):
    """Exchange a public token for an access token."""
    from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest

    client = _get_plaid_client()
    request = ItemPublicTokenExchangeRequest(public_token=public_token)
    response = client.item_public_token_exchange(request)
    return {
        'access_token': response.access_token,
        'item_id': response.item_id,
    }


def get_accounts(access_token):
    """Get accounts for a Plaid item."""
    from plaid.model.accounts_get_request import AccountsGetRequest

    client = _get_plaid_client()
    request = AccountsGetRequest(access_token=access_token)
    response = client.accounts_get(request)
    return [
        {
            'account_id': acct.account_id,
            'name': acct.name,
            'mask': acct.mask,
            'type': acct.type.value if hasattr(acct.type, 'value') else str(acct.type),
            'subtype': acct.subtype.value if acct.subtype and hasattr(acct.subtype, 'value') else str(acct.subtype) if acct.subtype else None,
            'current_balance': float(acct.balances.current) if acct.balances.current is not None else None,
        }
        for acct in response.accounts
    ]


def get_balances(access_token):
    """Get current balances for all accounts in a Plaid item."""
    from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest

    client = _get_plaid_client()
    request = AccountsBalanceGetRequest(access_token=access_token)
    response = client.accounts_balance_get(request)
    return [
        {
            'account_id': acct.account_id,
            'current_balance': float(acct.balances.current) if acct.balances.current is not None else None,
            'available_balance': float(acct.balances.available) if acct.balances.available is not None else None,
        }
        for acct in response.accounts
    ]
