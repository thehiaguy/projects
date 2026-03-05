#ifndef POST_H
#define POST_H

#include <string>

class Post{
public:
    Post();

    Post(int profileId ,int authorId ,std::string message, int likes);

    //pre:
    //post:
    int getMessageId();

    //pre:
    //post:
    void setMessageId(int id);

    //pre:
    //post:
    int getProfileId();

    //pre:
    //post:
    int getAuthorId();

    //pre:
    //post:
    std::string getMessage();

    //pre:
    //post:
    int getLikes();

    //pre:
    //post:
    virtual std::string getURL();

    //pre:
    //post:
    virtual std::string toString();

private:
    int messageId_;
    int profileId_;
    int authorId_;
    std::string message_;
    int likes_;

};

class LinkPost : public Post{
public:
    LinkPost();

    LinkPost(int profileId, int authorId, std::string message, int likes, std::string url);

    //pre:
    //post:
    std::string getURL();

    //pre:
    //post:
    std::string toString();

private:
    std::string url_;

};

#endif 