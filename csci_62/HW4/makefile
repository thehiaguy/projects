COMP = g++
FLAGS = -std=c++11 -Wall

ALL = social_network.o network.o user.o post.o

NOSOCIAL = network.o user.o post.o

TESTS = test_lpost1 test_lpost2 test_lpost3 test_lpost4 test_lpost5 test_lpost6

TESTS2 = test_network1 test_network2 test_network3 test_network4 test_network5

TEST3  = test_post1 test_post2 test_post3 test_post4 test_post5 test_post6 test_post7 test_post8 test_post9

social: $(ALL)
	$(COMP) $^ -o $@

.PHONY: alltest clean
alltest: $(TESTS)
alltest2 : $(TESTS2)
alltest3 : $(TEST3)

%.o : %.cpp 
	$(COMP) $(FLAGS) -c $< -o $@


$(TESTS) : %:%.o $(NOSOCIAL)
	$(COMP) $(FLAGS) $^ -o $@


$(TESTS2) : %:%.o $(NOSOCIAL)
	$(COMP) $(FLAGS) $^ -o $@


$(TEST3) : %:%.o $(NOSOCIAL)
	$(COMP) $(FLAGS) $^ -o $@
	
clean:
	rm -f $(ALL) social social.exe $(TESTS)