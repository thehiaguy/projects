#include "user.h"

User::User() {}

User::User(int id, std::string name, int year, int zip, std::set<int>friends){
    id_ = id;
    name_ = name;
    year_ = year;
    zip_ = zip;
    friends_ = friends;
}

//pre: none
//post: add's friend to user
void User::addFriend(int id){
    friends_.insert(id);
}

//pre: none 
//post: remove's friend from user
void User::deleteFriend(int id){
    friends_.erase(id);
}

//GETTERS
//pre: none 
//post: return user's ID
int User::getId() const{
    return id_;
}

//pre: none
//post: return user's name
std::string User::getName() const{
    return name_;
}

//pre: none 
//post: return user's date of birth
int User::getYear() const{
    return year_;
}

//pre: none 
//post: return user's zip code
int User::getZip() const{
    return zip_;
}

//pre: none
//post: return user's friends list
std::set<int>& User::getFriends(){
    return friends_;
}



