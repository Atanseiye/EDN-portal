from app.models import Language, RegulatorRoute, SourceCard

LANG_LABEL = {
    "english": "English",
    "yoruba": "Yorùbá",
    "hausa": "Hausa",
    "igbo": "Igbo",
}

FACTS = {
    "yoruba": {
        "complaint-path": "Ibi àkọ́kọ́ tí oníbàárà yẹ kí ó fi ẹ̀sùn rẹ̀ sí ni Ẹ̀ka Ìtẹ́wọ́gbà Ẹ̀sùn Oníbàárà (Customer Complaints Unit) ti ilé-iṣẹ́ pínpín iná. Bí a kò bá yanju ẹ̀sùn náà, a lè gbe e lọ sí aláṣẹ tó yẹ fún ìgbésẹ̀ míì.",
        "complaint-timeline": "NERC sọ pé ilé-iṣẹ́ DisCo yẹ kí ó yanju ẹ̀sùn oníbàárà tí a fi sílẹ̀ ní kíkọ́ láàárín ọjọ́ iṣẹ́ mẹ́ẹ̀dógún (15), gẹ́gẹ́ bí ìṣòro náà ṣe le tó.",
        "consumer-rights": "Oníbàárà iná ní ẹ̀tọ́ sí ìṣírò owó tó hàn gbangba, sí ìtẹ́wọ́gbà àti ìwádìí ẹ̀sùn, sí ìkìlọ̀ ní kíkọ́ ṣáájú gígé iná gẹ́gẹ́ bí òfin ṣe sọ, àti sí àtúnṣe tàbí ìpadà owó bí a bá gba owó ju.",
        "estimated-billing-cap": "NERC sọ pé oníbàárà tí kò ní mita tí a sì ń ṣe estimated billing fún un kò yẹ kí a gba owó ju energy cap tó wúlò fún feeder rẹ̀ lọ.",
        "faulty-meter-estimation": "NERC sọ pé bí a bá yọ mita tó bàjẹ́ tàbí tó ti di àtijọ́, DisCo kò yẹ kí ó fi oníbàárà sí estimated billing tí kò ní ìpìlẹ̀ nítorí pé wọn kò rọ́pò mita náà. Bí rirọ́pò kò bá ṣẹlẹ̀ ní àkókò billing, a yẹ kí a lo àárín gbùngbùn billing tàbí vending oṣù mẹ́ta tó ṣáájú.",
        "meter-replacement-duty": "NERC sọ pé DisCo ló ní ojúṣe láti tún mita tó bàjẹ́ ṣe tàbí rọ́pò rẹ̀ ní kíákíá, ó sì tọ́ka sí ọjọ́ iṣẹ́ méjì lẹ́yìn tí wọ́n bá mọ̀ pé mita náà ní àṣìṣe.",
        "meter-credit-balance": "NERC sọ pé oníbàárà àti aṣojú DisCo yẹ kí wọ́n kọ iye units tó kù sílẹ̀, kí a sì fi units náà sí mita tuntun láàárín wákàtí 48 lẹ́yìn fifi mita tuntun sílẹ̀.",
        "state-transition": "NERC ti sọ pé àwọn ìpínlẹ̀ kan ti gba àṣẹ ìṣàkóso ọ̀ràn iná inú ìpínlẹ̀. Ní irú ìpínlẹ̀ bẹ́ẹ̀, ẹ̀sùn tó jẹ́ ti inú ìpínlẹ̀ yẹ kí ó lọ sí State Electricity Regulatory Commission tó yẹ.",
        "safety-tampering": "NERC kìlọ̀ pé fífi ọwọ́ kan tàbí yíyí ohun èlò iná padà láìtọ́ lewu; ó yẹ kí a jabo ewu bẹ́ẹ̀ fún DisCo lẹ́sẹ̀kẹsẹ.",
    },
    "hausa": {
        "complaint-path": "Mataki na farko shi ne a kai korafi a rubuce zuwa sashen karbar korafin kwastomomi na kamfanin rarraba wutar lantarki. Idan ba a warware ba, ana iya daukaka korafin zuwa hukumar da ta dace.",
        "complaint-timeline": "NERC ta ce ana sa ran DisCo ta warware rubutaccen korafin kwastoma cikin kwanakin aiki 15, gwargwadon wahalar lamarin.",
        "consumer-rights": "Kwastoman wutar lantarki yana da hakkin samun bayyanannen lissafin kudi, gabatar da korafi a bincika, samun sanarwa kafin katsewa bisa ka'ida, da gyara ko mayar da kudin da aka caje fiye da kima.",
        "estimated-billing-cap": "NERC ta ce kwastoman da ba shi da mita da ake yi wa estimated billing bai kamata a caje shi sama da energy cap da ya dace da feeder dinsa ba.",
        "faulty-meter-estimation": "Idan an cire mita mai matsala kuma ba a maye gurbinsa ba, bai kamata DisCo ta yi arbitrary estimated billing ba. NERC ta bayyana amfani da matsakaicin billing ko vending na watanni uku da suka gabata idan ba a maye gurbin mita cikin lokacin billing ba.",
        "meter-replacement-duty": "NERC ta ce DisCo ce ke da alhakin gaggauta gyara ko maye gurbin mita mai matsala, tare da ambaton kwanakin aiki biyu bayan gano matsalar.",
        "meter-credit-balance": "NERC ta ce ragowar units a tsohon mita ya kamata a saka wa kwastoma cikin sa'o'i 48 bayan an shigar da sabon mita.",
        "state-transition": "A jihohin da suka kammala sauyin kula da wutar lantarki zuwa hukuma ta jiha, korafin cikin jihar ya kamata a kai wa hukumar wutar lantarki ta jihar.",
        "safety-tampering": "NERC ta gargadi cewa taba ko sauya kayan wutar lantarki ba bisa ka'ida ba yana da hadari; a kai rahoto ga DisCo nan da nan.",
    },
    "igbo": {
        "complaint-path": "Ebe mbụ onye ahịa kwesịrị itinye mkpesa bụ Customer Complaints Unit nke ụlọ ọrụ nkesa ọkụ. Ọ bụrụ na a naghị edozi mkpesa ahụ, enwere ike ibuga ya n'aka onye na-achịkwa ọkụ kwesịrị ekwesị.",
        "complaint-timeline": "NERC kwuru na a na-atụ anya ka DisCo dozie mkpesa e dere n'akwụkwọ n'ime ụbọchị ọrụ 15, dabere n'otú okwu ahụ siri sie ike.",
        "consumer-rights": "Onye ahịa ọkụ nwere ikike ịnata billing doro anya, itinye mkpesa ka a nyochaa ya, ịnata ọkwa tupu e gbanyụọ ọkụ dịka iwu si dị, na inweta mmezi ma ọ bụ nkwụghachi ma ọ bụrụ na e boro ya ego karịrị akarị.",
        "estimated-billing-cap": "NERC kwuru na onye ahịa na-enweghị mita nke a na-eme estimated billing agaghị enwe billing karịrị energy cap dabara na feeder ya.",
        "faulty-meter-estimation": "Ọ bụrụ na e wepụrụ mita mebiri emebi ma a dochighị ya, DisCo ekwesịghị itinye onye ahịa na arbitrary estimated billing. NERC kọwara iji nkezi billing ma ọ bụ vending nke ọnwa atọ gara aga ma ọ bụrụ na a naghị edochi mita n'oge billing.",
        "meter-replacement-duty": "NERC kwuru na DisCo bụ onye ọrụ ya bụ imezi ma ọ bụ dochie mita mebiri emebi ngwa ngwa, ma kwuo ụbọchị ọrụ abụọ mgbe achọpụtara nsogbu ahụ.",
        "meter-credit-balance": "NERC kwuru na units fọdụrụ na mita ochie kwesịrị ịbanye na mita ọhụrụ n'ime awa 48 mgbe etinyere mita ọhụrụ.",
        "state-transition": "N'ala steeti ndị ebufere nchịkwa ọkụ n'aka steeti, mkpesa gbasara ọkụ n'ime steeti kwesịrị ịga n'aka State Electricity Regulatory Commission kwesịrị ekwesị.",
        "safety-tampering": "NERC dọrọ aka ná ntị na imetụ ma ọ bụ gbanwee akụrụngwa ọkụ n'ụzọ na-ekwesịghị ekwesị dị ize ndụ; a ga-akọ ya ozugbo nye DisCo.",
    },
}

ROUTE_NOTE = {
    "yoruba": {
        "state": "Fún ẹ̀sùn iná tó jẹ́ ti inú ìpínlẹ̀ yìí, kọ́kọ́ fi ẹ̀sùn sí DisCo rẹ ní kíkọ́. Bí wọn kò bá yanju rẹ̀, gbe e lọ sí aláṣẹ iná ìpínlẹ̀ tó wà lókè.",
        "federal": "Kọ́kọ́ fi ẹ̀sùn sí Customer Complaints Unit ti DisCo rẹ ní kíkọ́. Bí wọn kò bá yanju rẹ̀, gbe e lọ sí NERC Consumer Forum tó yẹ, lẹ́yìn náà sí NERC.",
    },
    "hausa": {
        "state": "Ga korafin wutar lantarki na cikin wannan jiha, fara da rubutaccen korafi ga DisCo. Idan ba a warware ba, daukaka zuwa hukumar wutar lantarki ta jihar da aka nuna.",
        "federal": "Fara da rubutaccen korafi ga Customer Complaints Unit na DisCo. Idan ba a warware ba, daukaka zuwa NERC Consumer Forum sannan zuwa NERC.",
    },
    "igbo": {
        "state": "Maka mkpesa ọkụ dị n'ime steeti a, buru ụzọ dee mkpesa nye DisCo gị. Ọ bụrụ na a naghị edozi ya, bugara ya n'aka onye na-achịkwa ọkụ steeti e gosiri.",
        "federal": "Buru ụzọ dee mkpesa nye Customer Complaints Unit nke DisCo. Ọ bụrụ na a naghị edozi ya, bulie ya gaa NERC Consumer Forum kwesịrị ekwesị, mesịa gaa NERC.",
    },
}

DISCLAIMER = {
    "english": "PowerRights provides informational guidance from cited electricity-regulatory sources. It is not a regulator, law firm, or substitute for an official decision. Verify time-sensitive rules with the cited authority.",
    "yoruba": "PowerRights ń fúnni ní ìtọ́sọ́nà ìmọ̀ nípa àwọn òfin àti ìlànà iná láti inú àwọn orísun tó tọ́ka sí. Kì í ṣe aláṣẹ, ilé iṣẹ́ agbẹjọ́rò, tàbí aropo fún ìpinnu aláṣẹ. Jẹ́rìí àwọn ìlànà tó lè yí padà pẹ̀lú orísun tó tọ́ka sí.",
    "hausa": "PowerRights na ba da bayanin jagora daga ka'idojin wutar lantarki da aka ambata. Ba hukuma ba ce, ba ofishin lauya ba ce, kuma ba ta maye gurbin hukuncin hukuma. A tabbatar da dokokin da ka iya sauyawa daga majiyar da aka nuna.",
    "igbo": "PowerRights na-enye ozi nduzi sitere n'iwu na ụkpụrụ ọkụ eletrik e depụtara. Ọ bụghị ụlọ ọrụ nchịkwa ma ọ bụ ụlọ iwu, ọ naghịkwa anọchi mkpebi gọọmenti. Nyochaa iwu nwere ike ịgbanwe site na isi mmalite e gosiri.",
}


def localized_fact(doc_id: str, language: Language, fallback: str) -> str:
    if language == "english":
        return fallback
    return FACTS.get(language, {}).get(doc_id, fallback)


def localize_route(route: RegulatorRoute, language: Language) -> RegulatorRoute:
    if language == "english":
        return route
    note = ROUTE_NOTE.get(language, {}).get(route.level, route.note)
    return route.model_copy(update={"note": note})


def disclaimer_for(language: Language) -> str:
    return DISCLAIMER.get(language, DISCLAIMER["english"])


def localized_source_cards(docs: list[dict], language: Language) -> list[SourceCard]:
    cards = []
    for item in docs:
        cards.append(SourceCard(
            title=item["title"],
            authority=item["authority"],
            url=item["url"],
            excerpt=localized_fact(item.get("id", ""), language, item["text"]),
            updated=item.get("updated"),
        ))
    return cards
