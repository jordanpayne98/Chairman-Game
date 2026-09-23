"""Known cup obligations in integer pence; never invent unpublished prizes.

Records are payable instructions for the production cup validation state, not
postings into the playable career ledger. Counterparties make funding explicit.
"""
from copy import deepcopy


def _money(value, label):
    if type(value) is not int or value<0:raise ValueError('Invalid '+label+'.')
    return value


def official_payment(rules, *, fee_pence, travel_mode, miles=0,
                     fare_pence=0, meal_receipt_pence=0, played=True):
    """Rule 26: provided fee schedule plus receipted/standard travel expenses."""
    fee=_money(fee_pence,'official fee');_money(miles,'travel distance')
    _money(fare_pence,'fare');_money(meal_receipt_pence,'meal receipt')
    if travel_mode in ('car','motorcycle','bicycle'):
        if fare_pence:raise ValueError('Cannot claim mileage and a public-transport fare.')
        travel=miles*rules[travel_mode+'_pence_per_mile']
    elif travel_mode in ('rail','bus'):travel=fare_pence
    else:raise ValueError('Unsupported travel mode.')
    meal=min(meal_receipt_pence,rules['meal_receipt_cap_pence']) if miles>rules['meal_threshold_miles'] else 0
    # Half a penny rounds up, an explicit accounting implementation convention.
    if not played:fee=(fee+1)//2
    return dict(fee_pence=fee,travel_pence=travel,meal_pence=meal,total_pence=fee+travel+meal)


def record_match_payables(state, fixture_id, *, official_invoices=(), tv_award=None):
    """Idempotently record known obligations after a played match.

    An invoice supplies the independently approved official fee; no fee schedule
    is inferred. TV money needs an explicit association amount and allocation.
    Prize and gate distributions remain absent until sourced, not silently zero.
    """
    fixture=next(f for f in state['fixtures'] if f['id']==fixture_id)
    if fixture['result'] is None:raise ValueError('Payables require a completed fixture.')
    rules=state['definition']['financial_rules'];lines=[];known=set()
    for invoice in official_invoices:
        ident=invoice.get('id')
        if not isinstance(ident,str) or not ident or ident in known:raise ValueError('Missing or duplicate official invoice.')
        known.add(ident)
        if any(line['id']=='official:'+ident for fid,record in state['finance_records'].items()
               if fid!=fixture_id for line in record['lines']):
            raise ValueError('Official invoice is already recorded against another fixture.')
        if not invoice.get('official_id'):raise ValueError('Official payee is missing.')
        if invoice['claim'].get('played',True) is not True:raise ValueError('Completed match requires the full official fee.')
        payment=official_payment(rules['officials'],**invoice['claim'])
        lines.append(dict(id='official:'+ident,payer=fixture['home'],
            payee='official:'+invoice['official_id'],amount_pence=payment['total_pence'],kind='official_fee_and_expenses'))
    if fixture['round']=='final' and official_invoices:
        raise ValueError('Final official expenses require a separate association funding instruction.')
    if fixture['round']=='semi_final':
        lines.append(dict(id='away_compensation',payer='association:wales',payee=fixture['away'],
            amount_pence=rules['semifinal_away_compensation_pence'],kind='semifinal_away_compensation'))
    if tv_award is not None:
        if not tv_award.get('decision_id'):raise ValueError('TV award requires an association decision.')
        total=_money(tv_award.get('amount_pence'),'TV award')
        shares=tv_award.get('shares',{})
        if set(shares)!={fixture['home'],fixture['away']}:raise ValueError('TV award must specify both competing clubs.')
        if sum(_money(v,'TV share') for v in shares.values())!=total:raise ValueError('TV shares do not reconcile with the award.')
        for cid,amount in sorted(shares.items()):
            lines.append(dict(id='tv:'+tv_award['decision_id']+':'+cid,payer='association:wales',
                              payee=cid,amount_pence=amount,kind='tv_facility_award'))
    previous=state['finance_records'].get(fixture_id)
    combined={line['id']:deepcopy(line) for line in previous['lines']} if previous else {}
    prior_tv={key for key,line in combined.items() if line['kind']=='tv_facility_award'}
    incoming_tv={line['id'] for line in lines if line['kind']=='tv_facility_award'}
    if prior_tv and incoming_tv and prior_tv!=incoming_tv:
        raise ValueError('Fixture already has a different TV award decision.')
    for line in lines:
        if line['id'] in combined and combined[line['id']]!=line:
            raise ValueError('Recorded payables cannot be silently replaced.')
        combined[line['id']]=line
    record=dict(fixture=fixture_id,currency=rules['currency'],on=fixture['result']['on'],
                lines=sorted(combined.values(),key=lambda line:line['id']),
                scope='known_obligations_only; prize/gate schedules unresolved')
    state['finance_records'][fixture_id]=record
    return deepcopy(record)
