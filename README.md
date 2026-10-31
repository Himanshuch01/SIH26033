# KhetKhata (खेत खाता)

A Django marketplace for **SIH26033**: farmers and FPOs sell directly to consumers and bulk buyers,
with explainable price forecasting, transparent quality grading, and pooled (shared-truck) logistics.

## Run it (5 commands)

```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo     # demo users, crops, prices, listings, trucks, orders
python manage.py runserver
```

Open http://127.0.0.1:8000. Demo logins (password `demo123`):
farmers `gurpreet`, `harjinder`, `balwinder`, `jaswant`, `manpreet`, `sukhdev`;
buyers `sai_mess`, `langar_seva`, `rasoi`, `greenbasket`.
Admin: `python manage.py createsuperuser`, then /admin/.
Run tests: `python manage.py test`.

## What is unique

| Feature | Where | How it works |
|---|---|---|
| "Where did your rupee go?" | `market/services.py`, `market/_split.html` | Splits every basket into farmer share, platform fee and shared-truck cost, and compares with the typical mandi chain. |
| Shared-truck logistics | `logistics/models.py` | A truck has a fixed trip cost. Cost/kg = trip cost / booked kg, so it falls as the truck fills. A live HTMX meter shows your order's effect before you pay. |
| Requirement board | `market/models.py` (Requirement, Bid) | A mess posts "200 kg tomatoes a week". Several farmers bid and the buyer accepts bids until it is filled. |
| Explainable forecast | `pricing/services.py` | Weekly average, 4/12-week moving averages and a monthly seasonal index. Gives Hold / Sell now / Steady with the reasons in plain words. |
| Transparent grading | `market/models.py` | Three checks scored 1-3 give grade A/B/C. Grade sets the fair price band (A = mandi +10%, B = mandi, C = mandi -12%). |
| EN / हिं / ਪੰਜਾਬੀ toggle | `core/i18n.py` | Label dictionary in the session, plus Hindi and Punjabi crop names. |

## Real data

The seeded mandi prices are **sample data** (seasonal pattern + noise) so the forecast has history.
To use real Agmarknet / data.gov.in prices:
`python manage.py import_prices prices.csv` with columns `commodity, market, date, modal_price` (₹/quintal).
The 55% mandi-chain mark-up in `settings.py` (`RETAIL_MARKUP_PCT`) is an **assumption** you can change and justify in the viva.

## Django concepts covered (for the CA / viva)

- **Project structure:** 5 apps (`accounts`, `core`, `market`, `logistics`, `pricing`), settings, URL includes with namespaces
- **Models and ORM:** ForeignKey, unique_together, indexes, TextChoices, `aggregate(Sum)`, `annotate(Count)`, `select_related`, `prefetch_related`, `Q` objects, `select_for_update`
- **Custom user model:** `AbstractUser` with a `role` field (farmer / buyer)
- **Authentication and authorisation:** `LoginView`, `LogoutView`, `@login_required`, a custom `role_required` decorator, ownership checks
- **Forms:** `ModelForm`, `UserCreationForm`, custom `clean()` and `clean_<field>()` validation, widgets, `ModelChoiceField`
- **Views:** function-based and class-based (`ListView`, `DetailView`), POST-redirect-GET, `require_POST`, `transaction.atomic`
- **Sessions:** cart in `request.session` (`market/cart.py`), language choice
- **Templates:** inheritance, includes, custom filters and tags (`core/templatetags/ledger.py`), context processor
- **Static and media files:** CSS, vendored HTMX, ImageField uploads
- **Admin:** customised `ModelAdmin`, inlines, custom action (dispatch a truck)
- **Management commands:** `seed_demo`, `import_prices`
- **Messages framework, pagination, testing** (`market/tests.py`, 12 tests)

## Folder map

```
accounts/   custom User, register
core/       home, language toggle, template tags, context processor
market/     crops, listings, cart, orders, requirements, bids, dashboards
logistics/  delivery slots (shared trucks) and the live meter
pricing/    mandi prices, forecast, price hint
templates/  one folder per app    static/  css + htmx
```

Ideas to extend: payment gateway (Razorpay test mode), SMS alerts, FPO sub-accounts, real photo uploads from the farmer's phone.
