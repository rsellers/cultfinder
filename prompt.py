from pydantic import BaseModel, Field
from typing import Union

# Track the version of this prompt. Must be updated manually. 
__version__ = "1.0.2" 

class EmotionalClassifier(BaseModel):
    intensity: Union[int, None] = Field(description="""A number from 0 to 100 that represents the intensity of the emotional metric. Leave blank or null if this metric is not applicable or there is not enough information to determine a score.""")
    context: str = Field(description="""A one-sentence description that explains the reason behind the numeric rating. Leave blank or null if there is not enough information to determine context.""")

    class Config:
        extra = "forbid"  # Disallow any extra fields

class EmotionalMetric(BaseModel):
    concept_or_meme_strength: EmotionalClassifier = Field(description="""Evaluate how powerful and engaging the core idea or meme of the project is. 0 indicates the members are not focused on the idea, 100 indicates the topic is universally capitvating.""")
    fairness: EmotionalClassifier = Field(description="""Is the token or project perceived to be fair the participants? 0 indicates widespread suspicion or discontent, 100 indicates the project or idea is widely accepted as being economically fair and evenly distributed.""")
    VC_cabal: EmotionalClassifier = Field(description="""Is there a widespread sentiment that large insiders, venture capitalists with large allocations, or 'cabals' are in control of the trajectory of the token price? 0 indicates widespread belief that venture capitalists, insiders, whales, or cabals are in control, 100 indicates a widespread belief that the community-at-large is in control and not select insiders.""")
    sell_intent: EmotionalClassifier = Field(description="""Are people openly planning or in the process of selling tokens? 0 indicates an open and widespread expression of intent to sell by the community, 100 indicates widespread sentiments to 'hold forever' or have 'diamond hands' or 'price doesn't matter'.""")
    vibes: EmotionalClassifier = Field(description="""How good are the vibes within the chat log? 0 indicates widespread negativity, unsupportiveness and harshness, 100 an atmosphere of general support, encouragement and generosity.""")
    comunity_strength: EmotionalClassifier = Field(description="""Is this a tight-knit community? 0 indicates community members regard eachother as strangers, 100 indicates an intimate and personal connection between all participants.""")
    emotional_intensity: EmotionalClassifier = Field(description="""Is the discussion highly emotionally charged? 0 indicates a flat or dry discussion, 100 indicates a highly emotionally charged environment across all participants.""")
    stickiness: EmotionalClassifier = Field(description="""Ignoring repeated messages in a short period of time, do users return and contribute messages and discussion across many hours or days? 0 indicates most users do not return to make multiple messages throughout the session duration, 100 indicates all users are contributing throughout the duration of the chat log.""")
    socioeconomic: EmotionalClassifier = Field(description="""Reading from clues within the chat group such as mentions of low disposable income, poor upbringing, living in 3rd-world or marginalized communities, are members of this group of high or low socioeconomic status? 0 indicates all users are of low socioeconomic status, 100 indicates all users wealthy and well connected elites.""")
    price_action_focus: EmotionalClassifier = Field(description="""Is there a strong focus on the token price in the conversations? 0 indicates no discussion of price action, 100 indicates widespread reaction to price movements and overall fixation on price.""")
    perceived_maximum_upside: EmotionalClassifier = Field(description="""Do the participants express a strong belief in the potential of the project making them rich? 0 indicates widespread disbelief or suspicion that participation will make users rich, 100 indicates widespread belief users will become rich after holding this token.""")
    free_cult_labor: EmotionalClassifier = Field(description="""Are people volunteering significant time and effort for the project without compensation, for example: participating in social media 'raids', creating original memes, evangelizing the project? 0 indicates people are not participating in value accretive activites whatsoever, 100 indicates widespread value accretive participation across the whole set of participants.""")
    community_health: EmotionalClassifier = Field(description="""Does this appear to be a vibrant and growing community or is the community 'dead'? 0 indicates an anemic 'dead' community, 100 indicates a vibrant healthy community.""")
    buy_inquiry: EmotionalClassifier = Field(description="""Are newcomers asking where or how they can buy the token? 0 indicates nobody is asking where to buy the token, 100 indicates widespread inqueries about where or how to purchase.""")
    inspiration: EmotionalClassifier = Field(description="""Do community members derive a sense of inspiration and hope from the community? 0 indicates that nobody is expressing inspiration and hope, 100 indicates widespread expressions of inspiration and hope gained from participating in the group.""")

    class Config:
        extra = "forbid"  # Disallow any extra fields

class TopLineMetrics(BaseModel):
    message_count: Union[int, None] = Field(description="""Total messages contained within this chat log""")
    message_count_ex_bot: Union[int, None] = Field(description="""Total messages, excluding bot account activity (example: price bot, buy notification bot, spam, ban bot)""")
    
    date_min: Union[str, None] = Field(description="""The earliest date for a chat entry for this log""")
    date_max: Union[str, None] = Field(description="""The latest date for a chat entry for this log""")
    user_count: Union[int, None] = Field(description="""Number of unique individuals participating in the discussion.""")
    user_count_ex_bot: Union[int, None] = Field(description="""Number of unique individuals participating in the discussion, excluding bot account activity.""")

    class Config:
        extra = "forbid"  # Disallow any extra fields


class Reference(BaseModel):
    description: Union[str, None] = Field(description="""A concise, single sentence description of what the topic or account is based the context of the discussion.""")
    account_name: Union[str, None] = Field(description="""The account name being referenced in the chat, based on URL links to social media pages. example: @elonmusk. """)
    reference_count: Union[int, None] = Field(description="""the number of unique references to this account, in the form of URL links to social media pages.""")
    url: Union[str, None] = Field(description="""A complete URL to the social media profile being discussed, example: https://x.com/elonmusk.""")
    
    class Config:
        extra = "forbid"  # Disallow any extra fields

class ProjectReference(BaseModel):

    project_reference_1: Reference = Field(description="""The number one most popular crypto project under discussion in this log""")
    project_reference_2: Reference = Field(description="""The number two most popular crypto project under discussion in this log.""")
    project_reference_3: Reference = Field(description="""The number three most popular crypto project under discussion in this log.""")

    class Config:
        extra = "forbid"  # Disallow any extra fields

class SocialReference(BaseModel):

    social_reference_1: Reference = Field(description="""The most popular externally linked social media profile. Must be referenced via URL in chat log.""")
    social_reference_2: Reference = Field(description="""The second most popular externally linked social media profile. Must be referenced via URL in chat log.""")
    social_reference_3: Reference = Field(description="""The third most popular externally linked social media profile. Must be referenced via URL in chat log.""")
    social_reference_4: Reference = Field(description="""The fourth most popular externally linked social media profile. Must be referenced via URL in chat log.""")
    social_reference_5: Reference = Field(description="""The fifth most popular externally linked social media profile. Must be referenced via URL in chat log.""")
 

    class Config:
        extra = "forbid"  # Disallow any extra fields

class CommunityMetrics(BaseModel):
    #message: TopLineMetrics = Field(description="""High level usage and date metrics of the chat log""")
    emotional_metrics: EmotionalMetric = Field(description="""Metrics pertaining to differnt emotional qualities expressed by the participants of the chat.""")
    #project_reference: ProjectReference = Field(description="""Information and metrics pertaining to frequently referenced crypto projects.""")
    #social_reference: SocialReference = Field(description="""Information and metrics pertaining to frequently referenced social media acounts and influencers.""")

    class Config:
        extra = "forbid"  # Disallow any extra fields

class ChatLogAnalysisResponse(BaseModel):
    metrics: CommunityMetrics

    class Config:
        extra = "forbid"  # Disallow any extra fields
