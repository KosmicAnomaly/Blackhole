-- Creation of Counting Settings table
CREATE TABLE CountingSettings (
    guild_id BIGINT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT false,
    channel_id BIGINT UNIQUE,
    allow_math BOOLEAN NOT NULL DEFAULT false,
    modified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    modified_by_id BIGINT NOT NULL,
    CONSTRAINT valid_guild_id CHECK (guild_id >= 0),
    CONSTRAINT valid_channel_id CHECK (channel_id >= 0),
    CONSTRAINT valid_modified_by_id CHECK (modified_by_id >= 0)
);
-- Creation of Counting Data table
CREATE TABLE CountingData (
    guild_id BIGINT PRIMARY KEY,
    next_number INT NOT NULL DEFAULT 1,
    highscore INT NOT NULL DEFAULT 0,
    last_counted_member_id BIGINT,
    last_counted_message_id BIGINT UNIQUE,
    CONSTRAINT valid_guild_id CHECK (guild_id >= 0),
    CONSTRAINT valid_next_number CHECK (next_number >= 1),
    CONSTRAINT valid_highscore CHECK (highscore >= 0),
    CONSTRAINT valid_member_id CHECK (last_counted_member_id >= 0),
    CONSTRAINT valid_message_id CHECK (last_counted_message_id >= 0),
    FOREIGN KEY (guild_id) REFERENCES CountingSettings (guild_id) ON DELETE CASCADE ON UPDATE CASCADE
);
-- Creation of Leveling Settings table
CREATE TABLE LevelingSettings (
    guild_id BIGINT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT false,
    multiplier NUMERIC(2, 1) NOT NULL DEFAULT 1.0,
    stack_roles BOOLEAN NOT NULL DEFAULT true,
    blacklisted_role_id BIGINT UNIQUE,
    announce BOOLEAN NOT NULL DEFAULT true,
    level_up_message VARCHAR(200) NOT NULL DEFAULT '%{member} is now level **%{level}!**',
    modified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    modified_by_id BIGINT NOT NULL,
    CONSTRAINT valid_guild_id CHECK (guild_id >= 0),
    CONSTRAINT valid_multiplier CHECK (
        multiplier BETWEEN 0.2 AND 2.0
    ),
    CONSTRAINT valid_blacklisted_role_id CHECK (blacklisted_role_id >= 0),
    CONSTRAINT valid_level_up_message CHECK (
        LENGTH(level_up_message) BETWEEN 1 AND 200
    ),
    CONSTRAINT valid_modified_by_id CHECK (modified_by_id >= 0)
);
-- Creation of Member Experience table
CREATE TABLE MemberExperience (
    guild_id BIGINT NOT NULL,
    member_id BIGINT NOT NULL,
    experience INT NOT NULL DEFAULT 0,
    level SMALLINT NOT NULL DEFAULT 0,
    last_triggered TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_guild_id CHECK (guild_id >= 0),
    CONSTRAINT valid_member_id CHECK (member_id >= 0),
    CONSTRAINT valid_experience CHECK (experience >= 0),
    CONSTRAINT valid_level CHECK (level >= 0),
    PRIMARY KEY (guild_id, member_id),
    FOREIGN KEY (guild_id) REFERENCES LevelingSettings (guild_id) ON DELETE CASCADE ON UPDATE CASCADE
);
-- Creation of Leveling Roles table
CREATE TABLE LevelingRoles (
    guild_id BIGINT NOT NULL,
    role_id BIGINT PRIMARY KEY,
    required_level INT NOT NULL DEFAULT 0,
    CONSTRAINT valid_guild_id CHECK (guild_id >= 0),
    CONSTRAINT valid_role_id CHECK (role_id >= 0),
    CONSTRAINT valid_required_level CHECK (required_level > 0),
    CONSTRAINT unique_reward_role UNIQUE (guild_id, role_id),
    CONSTRAINT unique_level UNIQUE (guild_id, required_level),
    FOREIGN KEY (guild_id) REFERENCES LevelingSettings (guild_id) ON DELETE CASCADE ON UPDATE CASCADE
);
-- Creation of Starboard Settings table
CREATE TABLE StarboardSettings (
    guild_id BIGINT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT false,
    channel_id BIGINT UNIQUE,
    required_stars SMALLINT NOT NULL DEFAULT 2,
    modified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    modified_by_id BIGINT NOT NULL,
    CONSTRAINT valid_guild_id CHECK (guild_id >= 0),
    CONSTRAINT valid_channel_id CHECK (channel_id >= 0),
    CONSTRAINT valid_add_stars CHECK (required_stars >= 2),
    CONSTRAINT valid_modified_by_id CHECK (modified_by_id >= 0)
);
-- Creation of Starboard Messages table
CREATE TABLE StarboardMessages (
    guild_id BIGINT NOT NULL,
    source_message_id BIGINT PRIMARY KEY,
    starboard_message_id BIGINT NOT NULL UNIQUE,
    CONSTRAINT valid_guild_id CHECK (guild_id >= 0),
    CONSTRAINT valid_source_message_id CHECK (source_message_id >= 0),
    CONSTRAINT valid_starboard_message_id CHECK (starboard_message_id >= 0),
    FOREIGN KEY (guild_id) REFERENCES StarboardSettings (guild_id) ON DELETE CASCADE ON UPDATE CASCADE
);
-- Creation of TempVC Settings table
CREATE TABLE TempVCSettings (
    guild_id BIGINT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT false,
    channel_id BIGINT UNIQUE,
    modified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    modified_by_id BIGINT NOT NULL,
    CONSTRAINT valid_guild_id CHECK (guild_id >= 0),
    CONSTRAINT valid_channel_id CHECK (channel_id >= 0),
    CONSTRAINT valid_modified_by_id CHECK (modified_by_id >= 0)
);
-- Creation of TempVC Channels table
CREATE TABLE TempVCChannels (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT PRIMARY KEY,
    CONSTRAINT valid_guild_id CHECK (guild_id >= 0),
    CONSTRAINT valid_channel_id CHECK (channel_id >= 0),
    FOREIGN KEY (guild_id) REFERENCES TempVCSettings (guild_id) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE INDEX channel ON TempVCChannels (channel_id);
-- Creation of Polls table
CREATE TABLE Polls (
    view_custom_id uuid PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    message_id BIGINT UNIQUE NOT NULL,
    topic VARCHAR(100) NOT NULL,
    max_choices SMALLINT NOT NULL DEFAULT 1,
    option_1 VARCHAR(50) NOT NULL,
    option_2 VARCHAR(50) NOT NULL,
    option_3 VARCHAR(50),
    option_4 VARCHAR(50),
    option_5 VARCHAR(50),
    CONSTRAINT valid_guild_id CHECK (guild_id >= 0),
    CONSTRAINT valid_channel_id CHECK (channel_id >= 0),
    CONSTRAINT valid_message_id CHECK (message_id >= 0),
    CONSTRAINT valid_max_choices CHECK (
        max_choices BETWEEN 1 AND 4
    )
);
-- Creation of Poll Votes table
CREATE TABLE PollVotes (
    message_id BIGINT NOT NULL,
    member_id BIGINT NOT NULL,
    option SMALLINT NOT NULL,
    CONSTRAINT valid_message_id CHECK (message_id >= 0),
    CONSTRAINT valid_member_id CHECK (member_id >= 0),
    CONSTRAINT valid_option CHECK (
        option BETWEEN 1 AND 5
    ),
    CONSTRAINT unique_vote UNIQUE (message_id, member_id, option),
    FOREIGN KEY (message_id) REFERENCES Polls (message_id) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE INDEX message_member ON PollVotes (message_id, member_id);
-- Creation of Haiku Settings table
CREATE TABLE HaikuSettings (
    guild_id BIGINT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT false,
    channel_id BIGINT UNIQUE,
    announce BOOLEAN NOT NULL DEFAULT true,
    react BOOLEAN NOT NULL DEFAULT true,
    modified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    modified_by_id BIGINT NOT NULL,
    CONSTRAINT valid_guild_id CHECK (guild_id >= 0),
    CONSTRAINT valid_channel_id CHECK (channel_id >= 0),
    CONSTRAINT valid_modified_by_id CHECK (modified_by_id >= 0)
);
-- Creation of dRole Sets table
CREATE TABLE DRoleSets (
    set_id SERIAL PRIMARY KEY,
    view_custom_id uuid NOT NULL,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    title VARCHAR(100) NOT NULL,
    description VARCHAR(200),
    max_roles SMALLINT NOT NULL DEFAULT 25,
    CONSTRAINT valid_guild_id CHECK (guild_id >= 0),
    CONSTRAINT valid_channel_id CHECK (channel_id >= 0),
    CONSTRAINT valid_message_id CHECK (message_id >= 0),
    CONSTRAINT valid_max_droles CHECK (
        max_roles BETWEEN 1 AND 25
    )
);
CREATE INDEX guild_channel ON DRoleSets (guild_id, channel_id);
CREATE INDEX guild_channel_message ON DRoleSets (guild_id, channel_id, message_id);
-- Creation of dRoles table
CREATE TABLE DRoles (
    set_id SERIAL NOT NULL,
    role_id BIGINT NOT NULL,
    label VARCHAR(50) NOT NULL,
    description VARCHAR(50),
    emoji VARCHAR(55),
    CONSTRAINT valid_role_id CHECK (role_id >= 0),
    CONSTRAINT unique_label UNIQUE (set_id, label),
    PRIMARY KEY (set_id, role_id),
    FOREIGN KEY (set_id) REFERENCES DRoleSets (set_id) ON DELETE CASCADE ON UPDATE CASCADE
);
-- Creation of Reminders table
CREATE TABLE Reminders(
    reminder_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    reminder VARCHAR (200) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires TIMESTAMPTZ NOT NULL,
    CONSTRAINT valid_user_id CHECK (user_id >= 0)
);
-- Store the time that settings are updaated
CREATE FUNCTION handle_settings_updates() RETURNS TRIGGER AS $$ BEGIN NEW.modified_at = NOW();
RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';
-- Store the time that something is triggered
CREATE FUNCTION update_last_triggered() RETURNS TRIGGER AS $$ BEGIN NEW.last_triggered = NOW();
RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';
-- Store the time that the Counting settings were updated
CREATE TRIGGER update_counting_settings_ts BEFORE
UPDATE ON CountingSettings FOR EACH ROW
    WHEN (
        OLD.* IS DISTINCT
        FROM NEW.*
    ) EXECUTE PROCEDURE handle_settings_updates();
-- Store the time that the Leveling settings were updated
CREATE TRIGGER update_leveling_settings_ts BEFORE
UPDATE ON LevelingSettings FOR EACH ROW
    WHEN (
        OLD.* IS DISTINCT
        FROM NEW.*
    ) EXECUTE PROCEDURE handle_settings_updates();
-- Store the time that the Starboard settings were updated
CREATE TRIGGER update_starboard_settings_ts BEFORE
UPDATE ON StarboardSettings FOR EACH ROW
    WHEN (
        OLD.* IS DISTINCT
        FROM NEW.*
    ) EXECUTE PROCEDURE handle_settings_updates();
-- Store the time that the TempVC settings were updated
CREATE TRIGGER update_tempvc_settings_ts BEFORE
UPDATE ON TempVCSettings FOR EACH ROW
    WHEN (
        OLD.* IS DISTINCT
        FROM NEW.*
    ) EXECUTE PROCEDURE handle_settings_updates();
-- Store the time that the Haiku settings were updated
CREATE TRIGGER update_haiku_settings_ts BEFORE
UPDATE ON HaikuSettings FOR EACH ROW
    WHEN (
        OLD.* IS DISTINCT
        FROM NEW.*
    ) EXECUTE PROCEDURE handle_settings_updates();
-- Store XP-gain cooldowns
CREATE TRIGGER update_xp_gain_ts BEFORE
UPDATE ON MemberExperience FOR EACH ROW
    WHEN (
        OLD.* IS DISTINCT
        FROM NEW.*
    ) EXECUTE PROCEDURE update_last_triggered();