# Contributing

If you want to contribute to a project and make it better, your help is very welcome.
Contributing is also a great way to learn more about social coding on Github,
new technologies and their ecosystems and how to make constructive,
helpful bug reports, feature requests and the noblest of all contributions:
a good, clean pull request.

You can use templates to create a [**bug report**](ISSUE_TEMPLATE/bug_report.md),
[**feature request**](ISSUE_TEMPLATE/feature_request.md)
or your own [**pull request**](PULL_REQUEST_TEMPLATE.md).
Using these templates will greatly simplify your interaction with Universum team.
But **this is not mandatory**. We always welcome any help.


## How to make a clean pull request

### 0. [Fork](http://help.github.com/fork-a-repo/) the project repository from Github

This step is required because of current Universum access policies: you won't be able to commit
directly to Universum itself.


### 1. Clone your fork to your development environment

```sh
$ git clone https://github.com/YOUR-GITHUB-USERNAME/Universum.git
```
If you have trouble setting up GIT with GitHub in Linux,
or are getting errors like "Permission Denied (publickey)",
then you must [setup your GIT installation to work with GitHub](http://help.github.com/linux-set-up-git/)


### 2. Add the main Universum repository as an additional git remote called "upstream"

Go to the directory where you cloned Universum, normally, "Universum". Then enter the following command:
```sh
$ git remote add upstream git://github.com/Samsung/Universum.git
```

### 3. Make sure there is an issue created for the thing you are working on

All new features and bug fixes should have an associated issue to provide a single point of reference
for discussion and documentation. Take a few minutes to look through the existing issue list
for one that matches the contribution you intend to make. If you find one already on the issue list,
then please leave a comment on that issue indicating you intend to work on that item.
If you do not find an existing issue matching what you intend to work on, please open a new issue
for your item. This will allow the team to review your suggestion,
and provide appropriate feedback along the way.

> For small changes or documentation issues, you don't need to create an issue,
a pull request is enough in this case


### 4. Fetch the latest code from the Universum

```sh
$ git fetch upstream
```
You should make sure you are working on the latest code for every new contribution.


### 5. Create a new branch for your feature based on the current Universum 'master' branch

> It's very important since you will not be able to submit more than one pull request
from your account if you'll use master

Each separate bug fix or change should go in its own branch.
Branch names should be descriptive and start with the number of the issue that your code relates to.
If you aren't fixing any particular issue, just skip the number. For example:
```sh
$ git checkout upstream/master
$ git checkout -b 999-name-of-your-branch-goes-here
```

### 6. Do your magic, write your code

Make sure it works :)

> Please note we comply to [PEP 8](https://www.python.org/dev/peps/pep-0008/) and use Pylint to check
the code style. Please refer to `pylintrc` file in root directory if needed


### 8. Commit your changes

Add the files/changes you want to commit to the staging area with
```sh
$ git add path/to/my/file.c
```

Commit your changes with a descriptive commit message.
We tend to use [commit conventions](https://www.conventionalcommits.org/),
where the scope generally refers to the particular Universum module the change is related to.
For example:
```sh
$ git commit -m "fix(docs): update TeamCity guide according to new functionality"
```

### 9. Pull the latest Universum code from upstream into your branch

```sh
$ git pull --rebase upstream master
```
This ensures you have the latest code in your branch before you open your pull request.
If there are any merge conflicts, you should fix them now and commit the changes again.
This ensures that it's easy for the Universum team to merge your changes with one click.


### 10. Having resolved any conflicts, push your code to Github

```sh
$ git push -u origin 999-name-of-your-branch-goes-here
```

The `-u` parameter ensures that your branch will now automatically push and pull from the github branch.
That means if you type `git push` the next time it will know where to push to.


### 11. Open a pull request against upstream

Go to your repository on Github and click "Pull Request",
choose your branch on the right and enter the details in the comment box.
We tend to apply the same [conventions](https://www.conventionalcommits.org/)
to pull requests as to commits. To link the request to some issue,
just put issue number (e.g. `#999`) anywhere in the request name or description.
We also encourage [automatic issue closing](https://help.github.com/articles/closing-issues-using-keywords/).

> Note that each pull request should fix a single issue


### 12. Someone will review your code

Someone will review your code, and you might be asked to make some changes.
In this case please go to step #6 (you don't need to open another pull request
if your current one is still open). If your code is accepted it will be merged
into the main branch and become part of the next Universum release.
If not, don't be disheartened, different people need different features
and Universum can't be everything to everyone, your code will still be available
on Github as a reference for people who need it.


### 13. Cleaning it up

After your code was either accepted or declined you can delete branches you've worked with
from your local repository and `origin`.
```sh
$ git checkout master
$ git branch -D 999-name-of-your-branch-goes-here
$ git push origin --delete 999-name-of-your-branch-goes-here
```
