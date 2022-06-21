from .core import MpesaClient


def stk_push(phone_number, amount, trans_desc, callback_url):
    client = MpesaClient()
    account_ref = "KAT"
    response = client.stk_push(phone_number=phone_number, amount=amount,
                               account_reference=account_ref, transaction_desc=trans_desc, callback_url=callback_url)
    return response


def withdraw(phone_number, amount, trans_desc, callback_url):
    cl = MpesaClient()
    occassion = "Withdraw"
    response = cl.business_payment(phone_number, amount, transaction_desc=trans_desc, callback_url=callback_url,
                                    occassion=occassion)
    return response

