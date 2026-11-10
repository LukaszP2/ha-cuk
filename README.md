# CUK Strefa Klienta – Home Assistant Custom Component

[![GitHub Release](https://img.shields.io/github/v/release/LukaszP2/ha-cuk?style=flat-square)](https://github.com/LukaszP2/ha-cuk/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://hacs.xyz)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)


[![Otwórz repozytorium w HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=LukaszP2&repository=ha-cuk&category=integration)
[![Dodaj integrację do Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=cuk)

*(🇬🇧 English description below)*

---

## 🇵🇱 Opis

Integracja Home Assistant z portalem CUK Ubezpieczenia (Strefa Klienta). Automatyczne monitorowanie aktywnych polis, terminów płatności rat oraz ważności ubezpieczeń.

### Główne funkcje
- Podsumowanie aktywnych polis ubezpieczeniowych (komunikacyjne, nieruchomości, na życie)
- Powiadomienia o zbliżających się ratach i terminach płatności
- Daty końca ochrony ubezpieczeniowej z wyprzedzeniem
- Szczegółowe dane polis w atrybutach encji

### Instalacja przez HACS (Niestandardowe repozytorium)

### 🚀 Szybka instalacja (1 kliknięcie przez My Home Assistant)

[![Otwórz repozytorium w HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=LukaszP2&repository=ha-cuk&category=integration)

Po zainstalowaniu i ponownym uruchomieniu Home Assistant, kliknij poniższy przycisk, aby skonfigurować integrację:

[![Dodaj integrację do Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=cuk)



1. Upewnij się, że masz zainstalowany **HACS** w Home Assistant.
2. W HACS przejdź do: **Integracje** -> menu w prawym górnym rogu (trzy kropki) -> **Niestandardowe repozytoria** (*Custom repositories*).
3. W polu **Repozytorium** wklej adres:
   ```text
   https://github.com/LukaszP2/ha-cuk
   ```
4. W polu **Kategoria** wybierz: **Integracja** (*Integration*).
5. Kliknij **Dodaj**, a następnie wyszukaj **CUK Strefa Klienta** i kliknij **Pobierz**.
6. Uruchom ponownie Home Assistant.

### Konfiguracja

1. W Home Assistant przejdź do: **Ustawienia** -> **Urządzenia oraz usługi** -> **Dodaj integrację**.
2. Wyszukaj **CUK Strefa Klienta**.
3. Wprowadź **ObjectId użytkownika CUK**.

#### 🔑 Jak uzyskać ObjectId użytkownika?
1. Zaloguj się na swoje konto w portalu [strefaklienta.cuk.pl](https://strefaklienta.cuk.pl).
2. Otwórz narzędzia deweloperskie w przeglądarce (**F12**) i przejdź do zakładki **Sieć** (*Network*).
3. Odśwież stronę pulpitu i znajdź dowolne żądanie do API (np. `b2c/GetUser` lub `GetPolicies`).
4. W zakładce żądania (*Payload* / *Treść żądania*) odczytaj wartość pola `id` lub `userId` (ciąg znaków w formacie GUID, np. `a1b2c3d4-e5f6-7890-abcd-ef1234567890`).

### 📋 Gotowe szablony automatyzacji (Blueprinty)

Integracja dostarcza gotowe blueprinty ułatwiające monitorowanie ubezpieczeń:

1. **Ostrzeżenie o kończącej się polisie** (`blueprints/automation/cuk/policy_expiration_alert.yaml`)
   - Powiadomienie push z podsumowaniem kończących się polis (OC, AC, majątek).
   - Przycisk bezpośredniego połączenia telefonicznego z przypisanym opiekunem CUK oraz link do Strefy Klienta.
2. **Przypomnienie o racie płatności** (`blueprints/automation/cuk/installment_payment_reminder.yaml`)
   - Przypomnienie o zbliżającym się terminie wymagalności raty z kwotą, numerem raty i polisy.
   - Bezpośredni odnośnik do opłacenia składki.
3. **Alert o zaległej racie** (`blueprints/automation/cuk/overdue_installment_alert.yaml`)
   - Pilny alert (z możliwością obejścia wyciszenia / powiadomienia krytycznego), gdy termin płatności raty minął.

---

## 🇬🇧 Description

Home Assistant integration for CUK Insurance customer portal. Monitors active insurance policies, installment due dates, and policy expirations.

### Installation via HACS (Custom Repository)

1. Open **HACS** in Home Assistant.
2. Navigate to **Integrations** -> top right menu (three dots) -> **Custom repositories**.
3. Enter repository URL:
   ```text
   https://github.com/LukaszP2/ha-cuk
   ```
4. Category: **Integration**.
5. Click **Add**, find **CUK Strefa Klienta**, and install.
6. Restart Home Assistant.

### Configuration

1. In Home Assistant go to: **Settings** -> **Devices & Services** -> **Add Integration**.
2. Search for **CUK Strefa Klienta**.
3. Enter your **CUK user ObjectId**.

#### 🔑 How to find your user ObjectId?
1. Log in to your account at [strefaklienta.cuk.pl](https://strefaklienta.cuk.pl).
2. Open your browser Developer Tools (**F12**) and navigate to the **Network** tab.
3. Refresh the dashboard and inspect any API request (such as `b2c/GetUser` or `GetPolicies`).
4. In the request payload inspect the `id` or `userId` parameter (GUID format, e.g. `a1b2c3d4-e5f6-7890-abcd-ef1234567890`).

### 📋 Automation Blueprints

Ready-to-use Home Assistant automation blueprints included in `blueprints/automation/cuk/`:

1. **Policy Expiration Alert** (`policy_expiration_alert.yaml`) — Notifies about expiring policies with one-click call to your CUK insurance advisor.
2. **Installment Payment Reminder** (`installment_payment_reminder.yaml`) — Reminds of upcoming installment payments with amount and policy number.
3. **Overdue Installment Alert** (`overdue_installment_alert.yaml`) — Urgent/critical alert when an installment has passed its due date.


---

## Licencja / License

Projekt objęty licencją [MIT](LICENSE).