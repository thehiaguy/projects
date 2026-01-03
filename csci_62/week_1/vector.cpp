#include <iostream>
#include <vector>
#include <set>
using namespace std;


int main(){
//vector demo
	vector<int> vec;//initialize empty vector
	vec.push_back(0);
	vec.push_back(0);
	vec.push_back(1);
	vec[1] = 2;
	for (int i = 0; i<vec.size(); i++){
		cout << vec[i] << endl;

	}
	cout<<endl;

	for(int x : vec){
		cout<<x<<endl;
	}
	cout<<endl;
//set demo
	set<int> s;
	s.insert(6);
	s.insert(7);

	cout<<s.size()<<endl;
	for (int y : s){ // sets always itterate in an increasing order, because it utiizes a binary search tree
		cout<<y<<endl;
	}
}
