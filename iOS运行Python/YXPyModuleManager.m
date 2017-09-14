//
//  YXPyModuleManager.m
//  iOS运行Python
//
//  Created by  谭德林 on 2017/9/13.
//  Copyright © 2017年 yj. All rights reserved.
//

#import "YXPyModuleManager.h"

@implementation YXPyModuleManager
- (instancetype)initWithMoudleName:(NSString*)moduleName
                             pyURL:(NSURL*)pyURL{
    NSAssert(moduleName!=nil, @"can not be nit");
    NSAssert(pyURL!=nil, @"can not be nit");
    if (self = [super init]) {
        _moduleName = moduleName;
        _pyURL = pyURL;
    }
    return self;
}

- (void)downLoadPyResourceToLoaclModuleComplete:(void(^)(BOOL success))complete{
    dispatch_async(dispatch_get_global_queue(0, 0), ^{
        BOOL isEvn = [self configPythonEnvironment];
        if(!isEvn){
            if (complete) {
                complete(isEvn);
            }
            return ;
        }
        
        NSData *pyData = [NSData dataWithContentsOfURL:self.pyURL];
        
        if (pyData) {
            // 删除开始的模块
            [self deletePythonDirectory];
            //重新创建模块
            BOOL isSuccess = [self createModuleDirectory:self.moduleName pythonFilePath:self.pyURL.absoluteString pyData:pyData];
            dispatch_async(dispatch_get_main_queue(), ^{
                if (complete) {
                    complete(isSuccess);
                }
            });
        
        }else{
            dispatch_async(dispatch_get_main_queue(), ^{
                if (complete) {
                    complete(NO);
                }
            });
        }
    });
    
}

+ (void)downLoadPyResourceToLoaclModuleWithModuelName:(NSString*)moduleName pyURL:(NSURL*)pyURL complete:(void(^)(BOOL success))complete {
    YXPyModuleManager *moduelManger = [[YXPyModuleManager alloc] initWithMoudleName:moduleName pyURL:pyURL];
    [moduelManger downLoadPyResourceToLoaclModuleComplete:complete];
}

#pragma mark - private

- (void)deletePythonDirectory
{
    NSString *documantPath = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES).lastObject;
    NSString *python_home = [documantPath stringByAppendingPathComponent:@"Python.framework"];
    NSString * targetPath = [NSString stringWithFormat:@"%@/Resources/lib/python3.4/site-packages", python_home, nil];
    NSFileManager *fileManager = [NSFileManager defaultManager];
    NSArray *contentOfFolder = [fileManager contentsOfDirectoryAtPath:targetPath error:NULL];
    
    
    for (NSString *aPath in contentOfFolder) {
        NSString * fullPath = [targetPath stringByAppendingPathComponent:aPath];
        BOOL isDir = NO;
        if ([[NSFileManager defaultManager] fileExistsAtPath:fullPath isDirectory:&isDir])
        {
            if (isDir == YES) {
                if ([aPath rangeOfString:@"bs4"].location != NSNotFound
                    || [aPath rangeOfString:@"requests"].location != NSNotFound
                    || [aPath rangeOfString:@"urllib3"].location != NSNotFound
                    || [aPath rangeOfString:@"ICBC"].location != NSNotFound) {
                    continue;
                }
                NSError * error;
                [fileManager removeItemAtPath:fullPath error:&error];
            }
        }
    }
}

-(BOOL)createModuleDirectory:(NSString *)directoryName
            pythonFilePath:(NSString *)pythonFilePath
                      pyData:(NSData*)pyData

{
        NSString *documantPath = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES).lastObject;
        NSString *newFrameworkPath = [documantPath stringByAppendingPathComponent:@"Python.framework"];
        
        NSString * targetPath = [NSString stringWithFormat:@"%@/Resources/lib/python3.4/site-packages", newFrameworkPath, nil];
        NSError *error;
        NSFileManager *fileManager = [NSFileManager defaultManager];
        NSString *directryPath = [targetPath stringByAppendingPathComponent:directoryName];
        
        BOOL isDir = NO;
        if ([fileManager fileExistsAtPath:directryPath isDirectory:&isDir]) {
            if (isDir == YES) {
                return YES;
            }
        }
        [fileManager createDirectoryAtPath:directryPath withIntermediateDirectories:YES attributes:nil error:&error];
        if (error) {
            return NO;
        }
        
        //创建__init__文件
        NSString *filePath = [directryPath stringByAppendingPathComponent:@"__init__.py"];
        if (![fileManager fileExistsAtPath:filePath]) {
            [fileManager createFileAtPath:filePath contents:nil attributes:nil];
        }
    
        filePath = [directryPath stringByAppendingPathComponent:[pythonFilePath lastPathComponent]];
        [pyData writeToFile:filePath options:NSDataWritingAtomic error:&error];
        if (error) {
           return NO;
        }
        return YES;

}

-(BOOL)configPythonEnvironment
{
    NSBundle *mainBundle = [NSBundle mainBundle];
    NSString *bundlePath = [mainBundle pathForResource:@"PythonEnvironment" ofType:@"bundle"];
    BOOL isExist = [[NSFileManager defaultManager] fileExistsAtPath:bundlePath];
    if(!isExist) {
        return NO;
    }
    NSBundle *bundle = [NSBundle bundleWithPath:bundlePath];
    NSString *PythonPath = [bundle pathForResource:@"Python" ofType:@"framework"];
    isExist = [[NSFileManager defaultManager] fileExistsAtPath:PythonPath];
    if (!isExist) {
        return NO;
    }
    NSString *newFrameworkPath = [self p_pythonFrameworkPath];
    if ([[NSFileManager defaultManager] fileExistsAtPath:newFrameworkPath]) {
        return YES;
    }
    NSError * error;
    [[NSFileManager defaultManager] copyItemAtPath:PythonPath toPath:newFrameworkPath error:&error];
    if (error) {
        return NO;
    }
    return YES;;
}

- (NSString*)p_pythonFrameworkPath{
    NSString *documantPath = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES).lastObject;
    NSString *newFrameworkPath = [documantPath stringByAppendingPathComponent:@"Python.framework"];
    return newFrameworkPath;
}

@end
