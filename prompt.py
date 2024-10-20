from pydantic import BaseModel, Field
from typing import Union


class EmotionalClassifier(BaseModel):
    intensity: Union[int, None] = Field(description="""A number from 1 to 100 that represents the intensity of the emotional metric.""")
    context: str = Field(description="""A one-sentence description that explains the reason behind the numeric rating.""")

    class Config:
        extra = "forbid"  # Disallow any extra fields

class EmotionalMetric(BaseModel):
    concept_or_meme_strength: EmotionalClassifier = Field(description="""Evaluate how powerful and engaging the core idea or meme of the project is. 0 indicates the members are not focused on the idea, 100 indicates the topic is universally capitvating.""")
    fairness: EmotionalClassifier = Field(description="""Is the token or project perceived to be fair the participants? 0 indicates widespread suspicion or discontent, 100 indicates the project or idea is widely accepted as being economically fair and evenly distributed.""")
    comunity_strength: EmotionalClassifier = Field(description="""Is this a tight-knit community? 0 indicates community members regard eachother as strangers, 100 indicates an intimate and personal connection between all participants.""")
    emotional_intensity: EmotionalClassifier = Field(description="""Is the discussion highly emotionally charged? 0 indicates a flat or dry discussion, 100 indicates a highly emotionally charged environment across all participants.""")
    stickiness: EmotionalClassifier = Field(description="""Ignoring repeated messages in a short period of time, do users return and contribute messages and discussion across many hours or days? 0 indicates most users do not return to make multiple messages throughout the session duration, 100 indicates all users are contributing throughout the duration of the chat log.""")
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
    topic: Union[str, None] = Field(description="""one or two word name for the topic or account referenced in the chat.""")
    reference_count: Union[int, None] = Field(description="""the number of unique references for the topic or account over the course of the chat""")
    ca: Union[str, None] = Field(description="""A crypto contract address connected with for the topic or account being mentioned, example 0xac0f66379a6d7801d7726d5a943356a172549adb or 4vMsoUT2BWatFweudnQM1xedRLfJgJ7hswhcpz4xgBTy.""")
    url: Union[str, None] = Field(description="""A URL corresponding to the topic or account being mentioned being referenced.""")
    description: Union[str, None] = Field(description="""A concise, single sentence descriotion of what the topic or account is based the context of the discussion.""")
    
    class Config:
        extra = "forbid"  # Disallow any extra fields

class ProjectReference(BaseModel):

    project_reference_1: Reference = Field(description="""The number one most popular crypto project under discussion in this log""")
    project_reference_2: Reference = Field(description="""The number two most popular crypto project under discussion in this log.""")
    project_reference_3: Reference = Field(description="""The number three most popular crypto project under discussion in this log.""")
    project_reference_4: Reference = Field(description="""The number four most popular crypto project under discussion in this log.""")

    class Config:
        extra = "forbid"  # Disallow any extra fields

class SocialReference(BaseModel):

    social_reference_1: Reference = Field(description="""The number one most popular social media post or influencer under discussion in this log. For example, accounts from x.com, twitter.com, tiktok, youtube, snapchat, discord, telegram, etc.""")
    social_reference_2: Reference = Field(description="""The number two most popular social media post or influencer under discussion in this log. For example, accounts from x.com, twitter.com, tiktok, youtube, snapchat, discord, telegram, etc.""")
    social_reference_3: Reference = Field(description="""The number three most popular social media post or influencer under discussion in this log. For example, accounts from x.com, twitter.com, tiktok, youtube, snapchat, discord, telegram, etc.""")
    social_reference_4: Reference = Field(description="""The number four most popular social media post or influencer under discussion in this log. For example, accounts from x.com, twitter.com, tiktok, youtube, snapchat, discord, telegram, etc.""")
    social_reference_5: Reference = Field(description="""The number five most popular social media post or influencer under discussion in this log. For example, accounts from x.com, twitter.com, tiktok, youtube, snapchat, discord, telegram, etc.""")
    social_reference_6: Reference = Field(description="""The number six most popular social media post or influencer under discussion in this log. For example, accounts from x.com, twitter.com, tiktok, youtube, snapchat, discord, telegram, etc.""")
    social_reference_7: Reference = Field(description="""The number five most popular social media post or influencer under discussion in this log. For example, accounts from x.com, twitter.com, tiktok, youtube, snapchat, discord, telegram, etc.""")
    social_reference_8: Reference = Field(description="""The number six most popular social media post or influencer under discussion in this log. For example, accounts from x.com, twitter.com, tiktok, youtube, snapchat, discord, telegram, etc.""")


    class Config:
        extra = "forbid"  # Disallow any extra fields

class CommunityMetrics(BaseModel):
    message: TopLineMetrics = Field(description="""High level usage and date metrics of the chat log""")
    emotional_metrics: EmotionalMetric = Field(description="""Metrics pertaining to differnt emotional qualities expressed by the participants of the chat.""")
    project_reference: ProjectReference = Field(description="""Information and metrics pertaining to frequently referenced crypto projects.""")
    social_reference: SocialReference = Field(description="""Information and metrics pertaining to frequently referenced social media acounts and influencers.""")

    class Config:
        extra = "forbid"  # Disallow any extra fields

class ChatLogAnalysisResponse(BaseModel):
    metrics: CommunityMetrics

    class Config:
        extra = "forbid"  # Disallow any extra fields


# community_health: FieldMetric = Field(description="""How healthy and growing the community is, based on engagement and participation.""")
# total_unique_posters: FieldMetric = Field(description="""The tally of unique individuals posting in the chat log.""")
# posts_per_user_per_day: FieldMetric = Field(description="""Rank of the engagement level of users, based on their posts per day.""")
# perceived_maximum_upside: FieldMetric = Field(description="""Do the participants express a strong belief in the potential of the project making them rich?""")
# 
# price_action_focus: FieldMetric = Field(description="""Is there a strong focus on the token price in the conversations?""")
# 
# cultiness: FieldMetric = Field(description="""To what degree does the community show cult-like behavior?""")
# emotion_in_discussion: FieldMetric = Field(description="""How emotionally charged are the discussions? Is there a lot of passion or conflict?""")
# participation_stickiness: FieldMetric = Field(description="""How sticky is participation? Are users consistently returning to contribute over time?""")
# free_cult_labor: FieldMetric = Field(description="""Are people volunteering significant time and effort for the project without compensation?""")
# project_mentions: FieldMetric = Field(description="""A list of crypto projects mentioned in the chat log, ordered by frequency of mention.""")
