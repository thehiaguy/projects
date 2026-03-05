#ifndef SOCIALNETWORKWINDOW_H
#define SOCIALNETWORKWINDOW_H


#include <QMainWindow>
#include "network.h"


QT_BEGIN_NAMESPACE
namespace Ui {
class SocialNetworkWindow;
}
QT_END_NAMESPACE

class SocialNetworkWindow : public QMainWindow
{
    Q_OBJECT

public:
    SocialNetworkWindow(QWidget *parent = nullptr);
    ~SocialNetworkWindow();
    void loginCheck();

private:
    Ui::SocialNetworkWindow *ui;
    Network network_;
    User* loggedin_;
    User* display_;

    void updateProfile();
};
#endif // SOCIALNETWORKWINDOW_H
