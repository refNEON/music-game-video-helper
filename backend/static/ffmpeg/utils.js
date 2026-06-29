let messageId = 0;
export const getMessageID = () => {
    if (messageId >= Number.MAX_SAFE_INTEGER) {
        messageId = 0;
    }
    return ++messageId;
};
