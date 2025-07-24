import os
from boxsdk import Client, OAuth2, JWTAuth
from boxsdk.exception import BoxAPIException
from boxsdk.object.collaboration import CollaborationRole
from dotenv import load_dotenv
import pandas as pd
import io

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
DEVELOPER_TOKEN = os.getenv("DEVELOPER_TOKEN")

def authenticate_app_token():
    if not DEVELOPER_TOKEN:
        raise ValueError("DEVELOPER_TOKEN must be set in environment variables.")

    auth = OAuth2(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        access_token=DEVELOPER_TOKEN,
    )
    return auth, DEVELOPER_TOKEN

def run_user_example(client):
    me = client.user(user_id='me').get(fields=['login'])
    print(f'The email of the user is: {me["login"]}' )

def run_folder_examples(client):
    root_folder = client.folder(folder_id='0').get()
    print(f'The root folder is owned by: {root_folder.owned_by["login"]}' )

    items = root_folder.get_items(limit=100, offset=0)
    print('This is the first 100 items in the root folder:')
    for item in items:
        print("   " + item.name)

def analyze_excel_in_memory(client, file_name='metadata_ver2.xlsx'):
    try:
        root_folder = client.folder(folder_id='0')
        items = root_folder.get_items()
        file_id = None
        for item in items:
            if item.name == file_name:
                file_id = item.id
                break

        if file_id:
            box_file = client.file(file_id).get()
            file_content = box_file.content()
            excel_data = io.BytesIO(file_content)

            df = pd.read_excel(excel_data)
            print("df:\n",df)
            # print('nFirst 5 rows of the Excel file:')
            # print(df.head())
            # print('nInformation about the Excel file:')
            # print(df.info())
            # print('nBasic statistics of numerical columns:')
            # print(df.describe())
            # df.to_excel('output.xlsx', index=False)
        else:
            print(f'File {file_name} not found in Box root folder.' )
    except Exception as e:
        print(f'An error occurred during Excel analysis: {e}' )

def run_collab_examples(client):
    root_folder = client.folder(folder_id='0')
    collab_folder = root_folder.create_subfolder('collab folder')
    try:
        collaboration = collab_folder.add_collaborator('someone@example.com', CollaborationRole.VIEWER)
        print('Created a collaboration')
        try:
            modified_collaboration = collaboration.update_info(role=CollaborationRole.EDITOR)
            print(f'Modified a collaboration: {modified_collaboration.role}' )
        finally:
            collaboration.delete()
            print('Deleted a collaboration')
    finally:
        print(f'Delete folder collab folder succeeded: {collab_folder.delete()}' )

def rename_folder(client):
    root_folder = client.folder(folder_id='0')
    foo = root_folder.create_subfolder('foo')
    try:
        print(f'Folder {foo.get()["name"]}' ) + ' created'

        bar = foo.rename('bar')
        print(f'Renamed to {bar.get()["name"]}' )
    finally:
        print(f'Delete folder bar succeeded: {foo.delete()}' )

def get_folder_shared_link(client):
    root_folder = client.folder(folder_id='0')
    collab_folder = root_folder.create_subfolder('shared link folder')
    try:
        print(f'Folder {collab_folder.get().name}' ) + ' created'

        shared_link = collab_folder.get_shared_link()
        print('Got shared link:' + shared_link)
    finally:
        print(f'Delete folder collab folder succeeded: {collab_folder.delete()}' )

def upload_file(client):
    root_folder = client.folder(folder_id='0')
    file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'file.txt')
    a_file = root_folder.upload(file_path, file_name='i-am-a-file.txt')
    try:
        print(f'{a_file.get()["name"]}' ) + ' uploaded: '
    finally:
        print(f'Delete i-am-a-file.txt succeeded: {a_file.delete()}' )

def upload_accelerator(client):
    root_folder = client.folder(folder_id='0')
    file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'file.txt')
    a_file = root_folder.upload(file_path, file_name='i-am-a-file.txt', upload_using_accelerator=True)
    try:
        print(f'{a_file.get()["name"]}' ) + ' uploaded via Accelerator: '
        file_v2_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'file_v2.txt')
        a_file = a_file.update_contents(file_v2_path, upload_using_accelerator=True)
        print(f'{a_file.get()["name"]}' ) + ' updated via Accelerator: '
    finally:
        print(f'Delete i-am-a-file.txt succeeded: {a_file.delete()}' )

def rename_file(client):
    root_folder = client.folder(folder_id='0')
    file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'file.txt')
    foo = root_folder.upload(file_path, file_name='foo.txt')
    try:
        print(f'{foo.get()["name"]}' ) + ' uploaded '
        bar = foo.rename('bar.txt')
        print(f'Rename succeeded: {bool(bar)}' )
    finally:
        foo.delete()

def update_file(client):
    root_folder = client.folder(folder_id='0')
    file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'file.txt')
    file_v1 = root_folder.upload(file_path, file_name='file_v1.txt')
    try:
        file_v2_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'file_v2.txt')
        file_v2 = file_v1.update_contents(file_v2_path)
    finally:
        file_v1.delete()

def search_files(client):
    search_results = client.search().query(
        'i-am-a-file.txt',
        limit=2,
        offset=0,
        ancestor_folders=[client.folder(folder_id='0')],
        file_extensions=['txt'],
    )
    for item in search_results:
        item_with_name = item.get(fields=['name'])
        print('matching item: ' + item_with_name.id)
    else:
        print('no matching items')

def copy_item(client):
    root_folder = client.folder(folder_id='0')
    file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'file.txt')
    a_file = root_folder.upload(file_path, file_name='a file.txt')
    try:
        subfolder1 = root_folder.create_subfolder('copy_sub')
        try:
            a_file.copy(subfolder1)
            print(subfolder1.get_items(limit=10, offset=0))
            subfolder2 = root_folder.create_subfolder('copy_sub2')
            try:
                subfolder1.copy(subfolder2)
                print(subfolder2.get_items(limit=10, offset=0))
            finally:
                subfolder2.delete()
        finally:
            subfolder1.delete()
    finally:
        a_file.delete()

def move_item(client):
    root_folder = client.folder(folder_id='0')
    file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'file.txt')
    a_file = root_folder.upload(file_path, file_name='a file.txt')
    try:
        subfolder1 = root_folder.create_subfolder('move_sub')
        try:
            a_file.move(subfolder1)
            print(subfolder1.get_items(limit=10, offset=0))
            subfolder2 = root_folder.create_subfolder('move_sub2')
            try:
                subfolder1.move(subfolder2)
                print(subfolder2.get_items(limit=10, offset=0))
            finally:
                subfolder2.delete()
        finally:
            try:
                subfolder1.delete()
            except BoxAPIException:
                pass
    finally:
        try:
            a_file.delete()
        except BoxAPIException:
            pass

def get_events(client):
    print(client.events().get_events(limit=100, stream_position='now'))

def get_latest_stream_position(client):
    print(client.events().get_latest_stream_position())

def long_poll(client):
    print(client.events().long_poll())

def _delete_leftover_group(existing_groups, group_name):
    existing_group = next((g for g in existing_groups if g.name == group_name), None)
    if existing_group:
        existing_group.delete()

def run_groups_example(client):
    try:
        original_groups = client.groups()
        _delete_leftover_group(original_groups, 'box_sdk_demo_group')
        _delete_leftover_group(original_groups, 'renamed_box_sdk_demo_group')

        new_group = client.create_group('box_sdk_demo_group')
    except BoxAPIException as ex:
        if ex.status != 403:
            raise
        print('The authenticated user does not have permissions to manage groups. Skipping the test of this demo.')
        return

    print('New group:', new_group.name, new_group.id)

    new_group = new_group.update_info({'name': 'renamed_box_sdk_demo_group'}) 
    print("Group's new name:", new_group.name)

    me_dict = client.user().get(fields=['login'])
    me = client.user(user_id=me_dict['id'])
    group_membership = new_group.add_member(me, 'member')

    members = list(new_group.membership())

    print('The group has a membership of: ', len(members))
    print('The id of that membership: ', group_membership.object_id)

    group_membership.delete()
    print('After deleting that membership, the group has a membership of: ', len(list(new_group.membership())))

    new_group.delete()
    groups_after_deleting_demo = client.groups()
    has_been_deleted = not any(g.name == 'renamed_box_sdk_demo_group' for g in groups_after_deleting_demo)
    print('The new group has been deleted: ', has_been_deleted)

def run_metadata_example(client):
    root_folder = client.folder(folder_id='0')
    file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'file.txt')
    foo = root_folder.upload(file_path, file_name='foo.txt')
    print(f'{foo.get()["name"]}' ) + ' uploaded '
    try:
        metadata = foo.metadata()
        metadata.create({'foo': 'bar'}) 
        print(f'Created metadata: {metadata.get()}' )
        update = metadata.start_update()
        update.update('/foo', 'baz', 'bar')
        print(f'Updated metadata: {metadata.update(update)}' )
    finally:
        foo.delete()

def run_examples(auth):
    client = Client(auth)

    run_user_example(client)
    run_folder_examples(client)
    analyze_excel_in_memory(client)
    run_collab_examples(client)

def main():
    auth, _ = authenticate_app_token()
    run_examples(auth)
    os._exit(0)

if __name__ == '__main__':
    main()

