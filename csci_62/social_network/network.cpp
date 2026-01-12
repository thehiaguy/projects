#include "network.h"

Network::Network() {}


//pre: takes in id 
//post: returns pointer to the user
User* Network::getUser(int id){
    if (id <0 || id >= users_.size()){ //check the scope of the given id
        return nullptr; //if out of scope return null
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
    int id1 = getId(s1);//get the id of s1
    int id2 = getId(s2);//get the id of s2

    if (id1 == -1 || id2 == -1){//check if it exists
          return -1;
    }
      
    getUser(id1)->addFriend(id2);
    getUser(id2)->addFriend(id1);

    return 0;

}

//pre: takes in two strings 
//post: deletes a friend connection if it exists 
int Network::deleteConnection(std::string s1, std::string s2){
    int id1 = getId(s1);//get the id of s1
    int id2 = getId(s2);//get the id of s2

    if (id1 == -1 || id2 == -1){//chekc if it exists
          return -1;
    }
      
    getUser(id1)->deleteFriend(id2);
    getUser(id2)->deleteFriend(id1);

    return 0;
}

//pre: takes in name of user
//post: returns ID of the user
int Network::getId(std::string name){
    for (int i = 0; i<users_.size();i++){//check through the entire social network to see if the person exists
        if (users_[i]->getName() == name){//if exists return the id
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

//pre: none 
//post: initializes all of the network's info from file
void Network::readUsers(const char* fname){
    std::ifstream readFile(fname);
    if (!readFile.is_open()){ //error check
        std::cout<<"Could not open file: "<< fname << std::endl;
    }
    std::string line;
    std::getline(readFile, line);//puts the first line into the initialized string
    std::stringstream Total(line);//removes all the unnessary spaces and tabs
    int totalUser;
    Total >> totalUser;//put the cleaned stream into new variable to be called
    
    for (int i = 0; i < totalUser; i++){
        //to get id 
        std::getline(readFile,line);
        std::stringstream Id(line);
        int id;
        Id >> id;

        //to get name
        std::getline(readFile, line);
        std::string name = line.substr(1);//substr(1) so that i can skip the tab at 0th
        //no stringstream here because we need both the first and the last name

        //to get year
        std::getline(readFile, line);
        std::stringstream Year(line);
        int year;
        Year >> year;

        //to parse zip
        std::getline(readFile,line);
        std::stringstream Zip(line);
        int zip;
        Zip >> zip;

        //to parse friends list
        std::getline(readFile, line);
        std::stringstream Friends(line);
        std::set<int> friendsList;
        int friendsId;
        while (Friends >> friendsId){
            friendsList.insert(friendsId);
        }

        User* user = new User(id, name, year,zip,friendsList);//initialize the new user with all the new info
        users_.push_back(user);//then add to the vector of user pointers

        

    }
    readFile.close();
}

//pre: none 
//post: writes all of the network's information to a file 
void Network::writeUsers(const char*fname){
    std::ofstream outFile(fname);
    if (!outFile.is_open()){
        std::cout<<"Could not open file: "<< fname << std::endl;
    }
    outFile << users_.size() << std::endl; // writing total users

    for (int i = 0; i< users_.size(); i++){
        outFile << users_[i]->getId() <<std::endl; //get the id of the user
        outFile << "\t" << users_[i]->getName() << std::endl; // get the name of the user
        outFile << "\t" << users_[i]->getYear() << std::endl; // get the year of the user
        outFile << "\t" << users_[i]->getZip() << std::endl; // get the zip code of the user


        outFile<< "\t"; 
        //need to iterate through the set of friends within the ith position of the vector
        //access the current user's friends list then iterate through it and print it
        for (std::set<int>::iterator it = users_[i]->getFriends().begin();it != users_[i]->getFriends().end();it++){
            outFile<<*it<<" ";
        }
        outFile<<std::endl;
    }
    outFile.close();

}


