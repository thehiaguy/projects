#ifndef USER_H
#define USER_H

#include <string>
#include <set>

class User{
public:
    User();

    User(int id, std::string name, int year, int zip, std::set<int>friends);

    //pre: none
    //post: add's friend to user
    void addFriend(int id);

    //pre: none 
    //post: remove's friend from user
    void deleteFriend(int id);

//GETTERS
    //pre: none 
    //post: return user's ID
    int getId() const;

    //pre: none
    //post: return user's name
    std::string getName() const;

    //pre: none 
    //post: return user's date of birth
    int getYear() const;

    //pre: none 
    //post: return user's zip code
    int getZip() const;

    //pre: none
    //post: return user's friends list
    std::set<int>& getFriends();


private:
    int id_;
    std::string name_;
    int year_ ;
    int zip_;
    std::set<int> friends_;

};

#endif 
