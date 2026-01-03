#include "network.h"

Network::Network() {}


//pre: takes in id 
//post: returns pointer to the user
User* Network::getUser(int id){
    if (id <0 || id >= users_.size()){
        return nullptr;
    }
    return users_[id];
}

//pre: takes in pointer to the user
//post: add the user to the database 
void Network::addUser(User* n){
    users_.push_back(n);
}

//pre: takes in two strings 
//post: add a friend connection if does not exist yet 
int Network::addConnection(std::string s1, std::string s2){
    int id1 = getId(s1);
    int id2 = getId(s2);

    if (id1 == -1 || id2 == -1){
          return -1;
    }
      
    getUser(id1)->addFriend(id2);
    getUser(id2)->addFriend(id1);

    return 0;

}

//pre: takes in two strings 
//post: deletes a friend connection if it exists 
int Network::deleteConnection(std::string s1, std::string s2){
    int id1 = getId(s1);
    int id2 = getId(s2);

    if (id1 == -1 || id2 == -1){
          return -1;
    }
      
    getUser(id1)->deleteFriend(id2);
    getUser(id2)->deleteFriend(id1);

    return 0;
}

//pre: takes in name of user
//post: returns ID of the user
int Network::getId(std::string name){
    for (int i = 0; i<users_.size();i++){
        if (users_[i]->getName() == name){
            return i;
        }
    }
    return -1;
}

//pre: none 
//post: returns the number of users in network
int Network::numUsers(){
    return users_.size();
}


