# Sextortion focus: what's left to build

Guildward's positioning: **the tool that stops sextortion on Discord**: before (spot the setup), during (stop the kid paying or sending more, get images removed), after (warn others, link the next account). Start narrow here, widen later (bullying, scams, other platforms).

Already built: setup detection (flattery, age probes, move to Snapchat/Instagram), per-pair grooming stages in Guard, photo-request detection, pressure/threat detection, "I need help" sextortion steps (don't pay, don't send more, save evidence, Take It Down, Bris, Polisen), deletion alerts, alt links via the same handle or payment tag, evidence kit.

## To do

1. **Sextortion detection categories** (in the AI detector + private rules), each with lots of training examples:
   - threat to share images ("pay or I send it to all your friends/followers")
   - follower/friend-list threats ("I have your followers list")
   - payment demands: gift cards, crypto, CashApp/PayPal/Swish, "send money"
   - countdowns and urgency ("you have 1 hour")
   - fake teen persona openers (girl profile, "im 16", quick move to Snapchat/Instagram)
2. **A dedicated sextortion alert.** When a kid's check or Guard sees the threat stage, go straight to the sextortion help (immediate steps, Take It Down, offer to tell the trusted adult) instead of a generic warning. Guard should alert mods at top priority.
3. **Payment-tag tracking as a priority link.** CashApp, PayPal, Swish, crypto wallet addresses, gift card codes: one payment account across many victims is the strongest link between a gang's accounts. Weight it above other handles in shared flags.
4. **Messaging.** Lead with sextortion in the README, the bot's Discord description, the install page and the launch film.
