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


std::vector<int> Network::shortestPath(int from, int to){
    std::vector<bool>visited(numUsers(),0);
    std::vector<int>prev(numUsers(),-1);
    std::queue<int> q;

    if (from<0 || from>=numUsers() || to<0 || to>=numUsers()){
        return {};
    }

    if (from == to){
        return {from};
    }

    visited[from] = true;
    q.push(from);

    while(q.size()>0){
        int curr = q.front();
        q.pop();

        User* u = getUser(curr); //need a pointer to the curr User
        for(int neighbor: u->getFriends()){ // need to loop through the user's friends list with getter
            if (!visited[neighbor]){
                visited[neighbor] = true;
                q.push(neighbor);
                prev[neighbor] = curr;

                if(neighbor == to){// if the to is curr's friend
                    std::vector<int>path;
                    int curr2 = to;
                    while (curr2!=-1){
                        path.push_back(curr2);
                        curr2 = prev[curr2];
                    }
                    std::reverse(path.begin(),path.end());
                    return path;
                }
                
            }
        }
    } 
    return {};
}

std::vector<int> Network::distanceUser(int from, int& to, int distance){
    std::vector<int>dist(numUsers(),-1);
    std::vector<int>prev(numUsers(),-1);
    std::queue<int>q;


    if (from<0 || from>=numUsers()){
        to = -1;
        return {};
    }

    if (distance == 0){
        to = from;
        return {from};
    }

    dist[from] = 0;
    q.push(from);
    while(q.size()>0){
        int curr = q.front();
        q.pop();
        User* u = getUser(curr);
        for (int neighbor : u->getFriends()){
            if(dist[neighbor]==-1){
                dist[neighbor] = dist[curr] + 1;
                prev[neighbor] = curr;
                q.push(neighbor);

                if(dist[neighbor]== distance){
                    to = neighbor; //found the user at that distance
                    std::vector<int>path;
                    int curr2 = neighbor;
                    while (curr2!=-1){
                        path.push_back(curr2);
                        curr2 = prev[curr2];
                    }
                    std::reverse(path.begin(),path.end());
                    return path;
                }
            }
            
        }
    }
    to = -1; // there is no user
    return {};
}

std::vector<int> Network::suggestFriends(int who, int& score){
    //first we can only recommend people who are 2 distances away and above 
    //don't suggest people who are friends already and themselves
    //score is the amount of mutual friends
    //need to get the user first
    int max = 0;
    User* user = getUser(who);
    if(!user){
        score = 0;
        return {};
    }
    //need something to keep track of the score from the user's pov
    std::vector<int>trackScore(numUsers(),0);
    std::set<int>& userFriends = user->getFriends();

    for (int friends : userFriends){
        User* u = getUser(friends);
        if(!u) continue; 
        //looping through the friend's friendlist
        for (int mfriends: u->getFriends()){
            //need condition to check for original user and the original friend
            if(mfriends != who && userFriends.find(mfriends)==userFriends.end()){
                trackScore[mfriends]++;
            }
        }
    }
    //after going through everyone need to check what the max score is 
    for (int i : trackScore){
        if (i > max){
            max = i;
        }
    }
    //need to check edge case if user doesn't have friends 
    if (max == 0){
        score = 0;
        return {};
    }
    score = max;
    std::vector<int>suggestion;
    for (int i = 0; i < trackScore.size(); i ++){
        if(trackScore[i]== max){
            suggestion.push_back(i);
        }
    }

    return suggestion;
}

void Network::dfs(int curr, std::vector<bool> &visited, std::vector<int> &comp){
    visited[curr] = true;
    comp.push_back(curr);

    User* u = getUser(curr);
    if (u == nullptr) return;
    for(int neighbor: u->getFriends()){
        if(!visited[neighbor]){
            dfs(neighbor, visited, comp);
        }
    }
}

std::vector<std::vector<int>> Network::groups(){
    //a group of users who all have paths to each other but no edges to all the other 
    //users
    //implement DFS recursive version
    std::vector<std::vector<int>> allGroups;
    std::vector<bool> visited(numUsers(),0);

    for (int i =0; i< numUsers(); i++){
        if (!visited[i]){
            std::vector<int> curr;
            dfs(i,visited,curr);
            allGroups.push_back(curr);
        }
    }
    
    
    return allGroups;
}

void Network::addPost(Post* post){
    //we need to set the post id by it's chronological num order 
    int total = 0;
    for(const auto& userPosts : posts_){
        total += userPosts.size();
    }
    post->setMessageId(total);

    // need to check for the author's id then add it to that user's vector of posts
    int profileId = post->getProfileId();
    while(profileId>= posts_.size()){
        posts_.push_back(std::vector<Post*>());
    }
    posts_[profileId].push_back(post);
}

std::vector<Post*> Network::getPosts(int id){
    //check if the posts is valid 
    if (id < 0 || id>=posts_.size()){
        return std::vector<Post*>();
    }
    return posts_[id];
}


std::string Network::postDisplayString(Post* post){
    //need to get the post's author's name so we need to get the id
    int authorId = post->getAuthorId();
    std::string name = ""; // this is just a holder for the name
    if(authorId<users_.size()&&authorId>=0){//checking if the id is valid 
        name = users_[authorId]->getName();//call the name getter and put it back in the holder 
    }

    return name+ " wrote: " + post->toString();
    
}

std::string Network::getPostsString(int profileId, int howMany){
    if (profileId<0 || profileId>posts_.size()){
        return "";
    }
    // we need to get the user's posts
    std::vector<Post*> userPosts = posts_[profileId];

    //need to get teh most recent posts so the highest ids 
    //need a string holder to return 
    std::string holder; 
    int count = 0;
    //loop through the vector of user's post from the back(newest)
    for (int i = userPosts.size()-1;i>=0&& count< howMany;i--){
        holder+=postDisplayString(userPosts[i]);
        holder+="\n\n"; // add spacing between the posts
        count++;
    }
    return holder;
}

int Network::readPosts(char* fname){
    std::ifstream infile(fname);
    if(!infile) return -1;

    int amountPost;
    infile>>amountPost;

    for (int i =0; i <amountPost; i++){
        //first is post number 
        //second is post message
        //profileId
        //authorId
        //likes 
        //possibly url
        int postNum, profId, authorId, like;
        std::string message, url, line;//line to get the leftover \n

        infile >>postNum;
        std::getline(infile,line);
        std::getline(infile,message);

        infile>>profId;
        infile>>authorId;
        infile>>like;
        getline(infile,line);
        getline(infile,url);

        //need to get rid of the tab from the url because it's causing the print to have tab
        if(!url.empty() && url[0] == '\t'){
            url = url.substr(1);
        }
        //need to check the case for if there is url or not to initiliaze newPost

        

        Post* newPost;

        if(!url.empty() && url[0] == '\t'){
            url = url.substr(1);
        }

        
        if(url.empty()){
            newPost = new Post(profId,authorId,message,like);
        }
        else{
            newPost = new LinkPost(profId,authorId,message,like,url);
        }

        newPost->setMessageId(postNum);
        

        //need to push into the posts vector and if it's bigger than what we have now we push in another vecotr of Post pointer
        while (profId>=posts_.size()){
            posts_.push_back(std::vector<Post*>());
        }
        posts_[profId].push_back(newPost);

    }
    return 0;

}

int Network::writePosts(char* fname){
    std::ofstream outfile(fname);
    if(!outfile) return -1;

    //loading all the posts into a vector of Post*
    std::vector<Post*>allPost;
    for (const auto& posts: posts_){
        for(Post* point: posts){
            allPost.push_back(point);
        }
    }
    //sort the post by messageId 
    std::sort(allPost.begin(),allPost.end(),comparePost);//need to write a function to compare the post messageId

    outfile<<allPost.size()<<std::endl;

    for (Post* p : allPost) {
        outfile << p->getMessageId() << std::endl;
        outfile << "\t" << p->getMessage() << std::endl;
        outfile << "\t" << p->getProfileId() << std::endl;
        outfile << "\t" << p->getAuthorId() << std::endl;
        outfile << "\t" << p->getLikes() << std::endl;
        
        if (p->getURL().empty()) {
            outfile << "\t" << std::endl; 
        } else {
            outfile << "\t" << p->getURL() << std::endl;
        }
    }


}

bool Network::comparePost(Post* n, Post* m){
    return n->getMessageId() < m->getMessageId();
}